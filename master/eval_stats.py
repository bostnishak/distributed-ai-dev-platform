"""Release statistics: is the candidate really better, or was it luck? (exact McNemar, paired bootstrap, SPRT)."""

from __future__ import annotations

import math
import random


def mcnemar_exact(champion: list[bool], candidate: list[bool]) -> float:
    """Two-sided exact p-value on the scenarios where the two disagree."""
    if len(champion) != len(candidate):
        raise ValueError("aynı senaryolar karşılaştırılmalı")
    gained = sum(1 for a, b in zip(champion, candidate, strict=True) if b and not a)
    lost = sum(1 for a, b in zip(champion, candidate, strict=True) if a and not b)
    n = gained + lost
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(gained, lost) + 1)) / 2**n
    return min(1.0, 2 * tail)


def bootstrap_difference(champion: list[float], candidate: list[float], rounds: int = 4000, seed: int = 7) -> tuple[float, float]:
    """95% interval of mean(candidate - champion) over paired scenarios."""
    if len(champion) != len(candidate) or not champion:
        raise ValueError("eşli ve boş olmayan ölçümler gerekli")
    deltas = [b - a for a, b in zip(champion, candidate, strict=True)]
    rng = random.Random(seed)  # noqa: S311, RUF100 - reproducible resampling, not security
    means = sorted(sum(rng.choices(deltas, k=len(deltas))) / len(deltas) for _ in range(rounds))
    return means[int(0.025 * rounds)], means[int(0.975 * rounds) - 1]


def sprt(results: list[bool], low: float = 0.6, high: float = 0.8, alpha: float = 0.05) -> str:
    """Wald's test while results arrive: 'accept' (pass rate >= high), 'reject' (<= low) or 'continue'."""
    ratio = sum(math.log(high / low) if ok else math.log((1 - high) / (1 - low)) for ok in results)
    bound = math.log((1 - alpha) / alpha)
    if ratio >= bound:
        return "accept"
    return "reject" if ratio <= -bound else "continue"


def gate(champion: list[bool], candidate: list[bool]) -> tuple[bool, str]:
    """Promote only a candidate that is significantly better and loses no scenario the champion passed."""
    p = mcnemar_exact(champion, candidate)
    lost = [i for i, (a, b) in enumerate(zip(champion, candidate, strict=True)) if a and not b]
    if lost:
        return False, f"{len(lost)} senaryoda gerileme"
    better = sum(candidate) > sum(champion)
    return (better and p < 0.05), f"p={p:.4f}, {sum(champion)} -> {sum(candidate)} / {len(candidate)}"
