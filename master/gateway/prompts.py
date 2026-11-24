"""GW-16 & GW-17: Versioned Prompt Template Loader & Layered System Prompt Builder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

_GREETING_RE = re.compile(
    r"^\s*(selam|merhaba|hey|hi|hello|nasılsın|nasilsin|naber|günaydın|gunaydin|iyi akşamlar|test|teşekkür\w*)[!.?\s]*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    variables: tuple[str, ...]
    body: str

    def render(self, **kwargs: str) -> str:
        missing = [v for v in self.variables if v not in kwargs]
        if missing:
            raise ValueError(f"Prompt şablonu '{self.name}' için eksik değişken(ler): {missing}")
        return self.body.format(**kwargs) if self.variables else self.body


def load_template(name: str, prompts_dir: Path | None = None) -> PromptTemplate:
    base = prompts_dir or _PROMPTS_DIR
    path = base / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt şablonu bulunamadı: {path}")
    raw = path.read_text(encoding="utf-8")
    version = "1.0"
    variables: list[str] = []
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            header, body = parts[1], parts[2].strip()
            for line in header.splitlines():
                if line.startswith("version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("variables:"):
                    val = line.split(":", 1)[1].strip().strip("[]")
                    variables = [v.strip() for v in val.split(",") if v.strip()]
    return PromptTemplate(name=name, version=version, variables=tuple(variables), body=body)


def is_simple_greeting(prompt: str) -> bool:
    return bool(_GREETING_RE.match(prompt or ""))


def build_layered_system_prompt(**opts: Any) -> tuple[str, list[str]]:
    """GW-17: Assemble strictly ordered, budgeted system prompt layers and return (text, layer_names)."""
    mode_name = str(opts.get("mode_name", "general"))
    mode_rules = str(opts.get("mode_rules", ""))
    user_prefs_block = str(opts.get("user_prefs_block", ""))
    memory_block = str(opts.get("memory_block", ""))
    rag_context = str(opts.get("rag_context", ""))
    tools_hint = str(opts.get("tools_hint", ""))
    user_prompt = str(opts.get("user_prompt", ""))
    layers: list[tuple[str, str]] = []

    base_tpl = load_template("base_identity")
    layers.append((f"base_identity@v{base_tpl.version}", base_tpl.render()))

    sec_tpl = load_template("security_hierarchy")
    layers.append((f"security_hierarchy@v{sec_tpl.version}", sec_tpl.render()))

    if mode_rules:
        mode_tpl = load_template("mode_contracts")
        layers.append((f"mode_contract:{mode_name}@v{mode_tpl.version}", mode_tpl.render(mode_name=mode_name, contract_rules=mode_rules)))

    if user_prefs_block:
        layers.append(("user_preferences", user_prefs_block[:1200]))

    # Never inject cross-chat/semantic memory on trivial greetings
    if memory_block and not is_simple_greeting(user_prompt):
        layers.append(("relevant_memory", memory_block[:2800]))

    if rag_context:
        layers.append(("rag_context", rag_context[:4000]))

    if tools_hint:
        layers.append(("tools_context", tools_hint[:1500]))

    full_text = "\n\n".join(body for _, body in layers if body.strip())
    return full_text, [name for name, body in layers if body.strip()]
