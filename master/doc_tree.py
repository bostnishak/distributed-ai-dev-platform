"""Summarise a long document as a tree: parts, then groups of parts, then the whole, keeping line anchors.

Leaves are summarised from the text itself with quotes the code verifies; higher levels are written only from the
level below. Every section of the result says which lines it covers, so any sentence can be checked.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic import BaseModel, ValidationError

import atomic_io
import config
import doc_reader
import research
import untrusted
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)
_GROUP = 4


class Leaf(BaseModel):
    summary: str = ""
    quotes: list[str] = []


class Node(BaseModel):
    summary: str = ""


async def _ask(chat: research.Chat, prompt_file: str, user: str, model: type[BaseModel]) -> BaseModel | None:
    try:
        return model.model_validate_json(await chat(load_prompt(prompt_file), user, model.model_json_schema()))
    except (ValidationError, ValueError, OSError, RuntimeError) as exc:
        _log.warning("summary step failed: %s", exc)
        return None


def _spans(pieces: list[str]) -> list[tuple[int, int]]:
    line, out = 1, []
    for piece in pieces:
        count = piece.count("\n") + 1
        out.append((line, line + count - 1))
        line += count
    return out


def _checked(summary: str, source: str) -> str:
    """Sentences whose figures all appear in the source; others are dropped rather than trusted."""
    allowed = research._numbers(source)
    kept = [s.strip() for s in summary.replace("\n", " ").split(". ") if s.strip() and research._numbers(s) <= allowed]
    return ". ".join(kept).rstrip(".") + "." if kept else ""


def _tree_file(text: str) -> Path:
    return config.data_dir() / "doc_trees" / f"{hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]}.json"


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _store(path: Path, tree: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(path, json.dumps(tree, ensure_ascii=False, indent=1))


async def summarise(text: str, chat: research.Chat | None = None) -> AsyncIterator[tuple[str, str]]:
    """("status", message) while working, then one ("report", markdown)."""
    stored = _tree_file(text)
    if chat is None and (tree := _load(stored)):
        yield "status", "Bu belgenin özet ağacı diskte; model çağrılmadan kullanılıyor."
        yield "report", tree["report"]
        return
    ask = chat or research._ask
    pieces = doc_reader.parts(text)[: doc_reader._MAX_PARTS]
    spans = _spans(pieces)
    leaves: list[tuple[tuple[int, int], str, list[str]]] = []
    failed = 0
    for index, (piece, span) in enumerate(zip(pieces, spans, strict=True), start=1):
        yield "status", f"Bölüm özetleniyor {index}/{len(pieces)}..."
        leaf = await _ask(ask, "agent_summary_leaf.md", untrusted.guard(piece), Leaf)
        quotes = [q.strip() for q in leaf.quotes if len(q) >= 20 and research._flat(q) in research._flat(piece)][:2] if leaf else []
        summary = _checked(leaf.summary, piece) if leaf else ""
        if not summary:  # the range stays listed: a silently missing part would look like it said nothing
            failed += 1
            summary = f"(satır {span[0]}-{span[1]} için doğrulanabilir özet yazılamadı)"
        leaves.append((span, summary, quotes))
    if failed == len(leaves):
        yield "report", "Belge özetlenemedi (model geçerli bir özet döndürmedi)."
        return
    sections: list[tuple[tuple[int, int], str]] = []
    for start in range(0, len(leaves), _GROUP):
        group = leaves[start : start + _GROUP]
        span = (group[0][0][0], group[-1][0][1])
        joined = "\n".join(summary for _s, summary, _q in group)
        node = await _ask(ask, "agent_summary_node.md", joined, Node) if len(group) > 1 else None
        sections.append((span, _checked(node.summary, joined) if node and _checked(node.summary, joined) else joined))
    yield "status", "Genel özet yazılıyor..."
    everything = "\n".join(summary for _s, summary in sections)
    top = await _ask(ask, "agent_summary_node.md", everything, Node) if len(sections) > 1 else None
    out = ["## Genel özet", (_checked(top.summary, everything) if top else "") or everything, "", "## Bölümler"]
    out += [f"**Satır {a}-{b}:** {summary}" for (a, b), summary in sections]
    quoted = [f"- satır {doc_reader.line_of(text, q)}: \"{q}\"" for _s, _m, quotes in leaves for q in quotes][:8]
    if quoted:
        out += ["", "## Belgeden alıntılar", *quoted]
    if failed:
        out += ["", f"UYARI: {failed} parça özetlenemedi; o satır aralıkları yukarıda işaretli."]
    out += ["", f"_{len(pieces)} parçanın hepsi okundu; özet katmanlı (parça → bölüm → bütün) kuruldu. Kaynakta olmayan sayı içeren cümleler çıkarıldı._"]
    report = "\n".join(out)
    if not failed:
        _store(stored, {"report": report, "sections": [{"lines": list(span), "summary": s} for span, s in sections],
                        "leaves": [{"lines": list(span), "summary": s, "quotes": q} for span, s, q in leaves]})
    yield "report", report
