"""Hierarchical budgets for a run, its stages and its steps: tokens, seconds and attempts.

A charge goes up the chain, so a step can never spend more than its stage or run has left. An overrun raises
BudgetExceeded; the caller rolls back to the last verified state instead of waiting forever.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

ACTIVE: ContextVar[Budget | None] = ContextVar("active_budget", default=None)
_DEFAULTS = {"run": (600_000, 7200.0, 300), "stage": (300_000, 3600.0, 150), "step": (150_000, 2400.0, 80)}  # a sliced or skeleton-first file makes many calls


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Budget:
    name: str
    tokens: int
    seconds: float
    attempts: int
    parent: Budget | None = None
    used_tokens: int = 0
    used_attempts: int = 0
    started: float = field(default_factory=time.monotonic)

    def child(self, name: str, kind: str = "step") -> Budget:
        return Budget(name, *limits(kind), parent=self)

    def _chain(self) -> Iterator[Budget]:
        node: Budget | None = self
        while node:
            yield node
            node = node.parent

    def remaining_seconds(self) -> float:
        return min(b.seconds - (time.monotonic() - b.started) for b in self._chain())

    def check(self) -> None:
        for budget in self._chain():
            if budget.used_tokens > budget.tokens:
                raise BudgetExceeded(f"{budget.name}: jeton bütçesi aşıldı ({budget.used_tokens}/{budget.tokens})")
            if budget.used_attempts > budget.attempts:
                raise BudgetExceeded(f"{budget.name}: deneme sayısı aşıldı ({budget.used_attempts}/{budget.attempts})")
            if time.monotonic() - budget.started > budget.seconds:
                raise BudgetExceeded(f"{budget.name}: süre bütçesi aşıldı ({budget.seconds:.0f} sn)")

    def charge(self, tokens: int = 0, attempts: int = 0) -> None:
        for budget in self._chain():
            budget.used_tokens += tokens
            budget.used_attempts += attempts
        self.check()


def limits(kind: str) -> tuple[int, float, int]:
    """(tokens, seconds, attempts) of one level, overridable as BUDGET_RUN_SECONDS, BUDGET_STEP_TOKENS, ..."""
    tokens, seconds, attempts = _DEFAULTS[kind]
    prefix = f"BUDGET_{kind.upper()}_"
    return int(os.environ.get(prefix + "TOKENS", tokens)), float(os.environ.get(prefix + "SECONDS", seconds)), int(os.environ.get(prefix + "ATTEMPTS", attempts))


def run_budget(name: str) -> Budget:
    return Budget(name, *limits("run"))


@contextmanager
def active(budget: Budget) -> Iterator[Budget]:
    token = ACTIVE.set(budget)
    try:
        yield budget
    finally:
        ACTIVE.reset(token)


def spend(tokens: int = 0, attempts: int = 0) -> None:
    """Charges whatever budget is in force; a call outside any run is free."""
    if budget := ACTIVE.get():
        budget.charge(tokens, attempts)


async def within(budget: Budget, work: Awaitable[Any]) -> Any:
    """The step's result, or BudgetExceeded when it stalls past the time that is left (the step is cancelled)."""
    with active(budget):
        task = asyncio.ensure_future(work)  # created inside, so the step sees this budget
    try:
        return await asyncio.wait_for(task, max(0.0, budget.remaining_seconds()))
    except TimeoutError as exc:
        raise BudgetExceeded(f"{budget.name}: adım {budget.seconds:.0f} sn içinde bitmedi ve durduruldu") from exc
