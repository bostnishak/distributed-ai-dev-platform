"""Strict hand-off schemas between the agents, with the Intake and Architect agents that fill them.

Colours, sizes and quoted labels are read from the text without a model; only button behaviour, forbidden items and
critical warnings come from the model, constrained to the JSON schema.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

import llm
import spec_contract
from prompt_loader import load_prompt

_Chat = Callable[[str, str, dict, int], Awaitable[str]]
_NUM_CTX = 8192


class ButtonRule(BaseModel):
    label: str
    behavior: str


class EndpointRule(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str


class IntakeAnswer(BaseModel):
    task_type: Literal["WEB_APP", "API_BACKEND", "FLOWCHART", "PDF_DOC", "IMAGE_ASSET", "REFACTOR", "MULTI_MODAL_COMPOSITE"] = "WEB_APP"
    buttons: list[ButtonRule] = Field(default_factory=list, max_length=20)
    forbidden: list[str] = Field(default_factory=list, max_length=10)
    regions: list[str] = Field(default_factory=list, max_length=8)  # header, sidebar, panels the user named
    endpoints: list[EndpointRule] = Field(default_factory=list, max_length=20)
    persistence: str = ""  # what must survive a restart, as the user said it


class SpecificationContract(IntakeAnswer):
    colors: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)


class Warning_(BaseModel):
    issue: str
    alternative: str


class ArchitectReview(BaseModel):
    warnings: list[Warning_] = Field(default_factory=list, max_length=3)
    assumptions: list[str] = Field(default_factory=list, max_length=3)


async def _ask(chat: _Chat, prompt_file: str, request: str, model: type[BaseModel]) -> BaseModel:
    """One schema-constrained call; an unreachable or invalid model gives the empty answer, never invented content."""
    try:
        return model.model_validate_json(await (chat or llm.chat_structured)(load_prompt(prompt_file), request[:6000], model.model_json_schema(), _NUM_CTX))
    except (llm.LLMError, ValidationError, ValueError):
        return model()


async def intake(request: str, chat: _Chat | None = None) -> SpecificationContract:
    answer = await _ask(chat, "agent_intake.md", request, IntakeAnswer)
    named = request.casefold()
    answer.buttons = [b for b in answer.buttons if b.label.casefold() in named]  # a button the user never named is a hallucination
    answer.endpoints = [e for e in answer.endpoints if e.path.casefold() in named]  # likewise an endpoint
    answer.regions = [r for r in answer.regions if any(w in named for w in r.casefold().split() if len(w) > 2)]
    if answer.persistence and not any(w in named for w in ("sakla", "kaydet", "kalıcı", "kalsın", "yenilen", "localstorage", "veritaban", "sqlite", "persist", "database", "save", "store")):
        answer.persistence = ""
    return SpecificationContract(**answer.model_dump(), **spec_contract.extract(request))


async def review(request: str, chat: _Chat | None = None) -> ArchitectReview:
    return await _ask(chat, "agent_architect.md", request, ArchitectReview)


def writer_notes(spec: SpecificationContract) -> str:
    """The contract as extra instructions for the file writers."""
    lines = [f"- '{b.label}' düğmesi: {b.behavior}" for b in spec.buttons]
    if spec.sizes:
        lines.append(f"- Ölçüler CSS'te aynen kullanılacak: {', '.join(spec.sizes)}")
    lines += [f"- YASAK: {item}" for item in spec.forbidden]
    return "\n\nTARİF SÖZLEŞMESİ (birebir uy):\n" + "\n".join(lines) if lines else ""
