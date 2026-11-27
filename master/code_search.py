"""Find the code that does something: words (BM25), symbol names and meaning (CPU embeddings), fused by rank."""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable
from pathlib import Path

import httpx

import code_graph
import long_doc
from gateway import local_gpu

_log = logging.getLogger(__name__)
_ASK_RE = re.compile(r"^\s*(?:projede|kodda)\s+(?P<what>.{3,200}?)\s+(?:nerede|hangi\s+dosyada)(?:\s+\w+){0,3}\??\s*$|^\s*search\s+code\s+for\s+(?P<en>.{3,200})$", re.IGNORECASE)
_SKIP = {".history", "venv", ".venv", "__pycache__", "node_modules"}
_SUFFIXES = {".py", ".js", ".ts", ".html", ".css", ".sql"}
_K = 60

Embed = Callable[[list[str]], list[list[float]]]


def chunks(ws_dir: Path) -> list[tuple[str, int, int, str]]:
    out = []
    for path in sorted(ws_dir.rglob("*")):
        if path.suffix in _SUFFIXES and path.is_file() and not _SKIP & set(path.relative_to(ws_dir).parts):
            out += [(path.relative_to(ws_dir).as_posix(), first, last, text) for first, last, text in long_doc.passages(path.read_text(encoding="utf-8", errors="replace"))]
    return out[:400]


def _ranks(scores: list[float]) -> dict[int, int]:
    order = sorted((i for i, s in enumerate(scores) if s > 0), key=lambda i: -scores[i])
    return {index: rank for rank, index in enumerate(order, start=1)}


def _meaning(query: str, parts: list[tuple[str, int, int, str]], embed: Embed) -> list[float]:
    try:
        vectors = embed([query, *[f"{p[0]}\n{p[3][:800]}" for p in parts]])
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        _log.warning("code search without embeddings: %s", exc)
        return [0.0] * len(parts)
    first = vectors[0]

    def cosine(other: list[float]) -> float:
        norm = math.sqrt(sum(a * a for a in first)) * math.sqrt(sum(b * b for b in other))
        return sum(a * b for a, b in zip(first, other, strict=False)) / norm if norm else 0.0

    return [cosine(v) for v in vectors[1:]]


def search(ws_dir: Path, query: str, top: int = 5, embed: Embed = local_gpu.embed) -> list[tuple[str, int, int, str]]:
    parts = chunks(ws_dir)
    if not parts:
        return []
    words = _ranks(long_doc._scores([(p[1], p[2], p[3]) for p in parts], query))
    symbols = code_graph.build_workspace_code_graph(ws_dir)["symbols"]
    wanted = set(long_doc._tokens(query))
    names = _ranks([float(len(wanted & set(long_doc._tokens(" ".join(f["name"] for f in symbols.get(p[0], {}).get("functions", []) if f["name"] in p[3]).replace("_", " ")))))
                    for p in parts])
    meaning = _ranks(_meaning(query, parts, embed))
    fused = {i: sum(1 / (_K + table[i]) for table in (words, names, meaning) if i in table) for i in range(len(parts))}
    return [parts[i] for i in sorted(fused, key=lambda i: -fused[i])[:top] if fused[i] > 0]


def asked(prompt: str) -> str:
    match = _ASK_RE.match(prompt)
    return (match["what"] or match["en"]).strip() if match else ""


def answer(ws_dir: Path, query: str) -> str:
    found = search(ws_dir, query)
    if not found:
        return "Bu sorguyla ilgili kod bulamadım."
    blocks = []
    for name, first, last, text in found[:3]:
        preview = "\n".join(text.splitlines()[:8])
        blocks.append(f"**{name}** (satır {first}-{last})\n```\n{preview}\n```")
    others = ", ".join(f"{n}:{a}" for n, a, _b, _t in found[3:])
    return f"`{query}` için en ilgili yerler:\n\n" + "\n\n".join(blocks) + (f"\n\nDiğer adaylar: {others}" if others else "")
