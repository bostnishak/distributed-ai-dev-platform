"""Long uploads: instead of the first N characters, give the model the passages that answer the question, with line anchors.

The whole document is cut into passages and ranked (BM25) against the request; the opening and closing passages are
always kept, as are lines that look like headings, so the model also sees the document's shape.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"\w{2,}")
_HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s|\d+(?:\.\d+)*[.)]\s+\S|[A-ZÇĞİÖŞÜ0-9 ]{6,}$|(?:bölüm|chapter|madde|section)\b)", re.IGNORECASE)
_CHUNK_CHARS = 900
_STEM = 5  # Turkish suffixes: compare the first letters only


def _tokens(text: str) -> list[str]:
    return [w[:_STEM] for w in _WORD_RE.findall(text.casefold())]


def passages(text: str) -> list[tuple[int, int, str]]:
    """(first line, last line, text) blocks of roughly equal size, never splitting a line unless it is huge."""
    out: list[tuple[int, int, str]] = []
    buffer: list[str] = []
    first, size = 1, 0
    for number, line in enumerate(text.splitlines(), start=1):
        for piece in (line[i : i + _CHUNK_CHARS] for i in range(0, max(len(line), 1), _CHUNK_CHARS)):
            if buffer and size + len(piece) > _CHUNK_CHARS:
                out.append((first, number, "\n".join(buffer)))
                buffer, size, first = [], 0, number
            buffer.append(piece)
            size += len(piece) + 1
    if buffer:
        out.append((first, first + len(buffer) - 1, "\n".join(buffer)))
    return out


def _scores(blocks: list[tuple[int, int, str]], query: str) -> list[float]:
    docs = [Counter(_tokens(b[2])) for b in blocks]
    wanted = set(_tokens(query))
    seen = {t: sum(1 for d in docs if t in d) for t in wanted}
    average = sum(sum(d.values()) for d in docs) / max(len(docs), 1)
    result = []
    for doc in docs:
        length = sum(doc.values())
        result.append(sum(math.log(1 + (len(docs) - seen[t] + 0.5) / (seen[t] + 0.5)) * doc[t] * 2.2 / (doc[t] + 1.2 * (0.25 + 0.75 * length / max(average, 1)))
                          for t in wanted if doc[t]))
    return result


def select(text: str, query: str, limit: int) -> str:
    """The text itself when it fits, otherwise outline plus the most relevant passages, in document order."""
    if len(text) <= limit:
        return text
    blocks = passages(text)
    headings = [f"satır {n}: {line.strip()[:90]}" for n, line in enumerate(text.splitlines(), start=1) if _HEADING_RE.match(line)][:60]
    outline = "\n".join(headings)[: limit // 6]
    scores = _scores(blocks, query)
    order = [0, len(blocks) - 1, *sorted(range(len(blocks)), key=lambda i: -scores[i])]
    chosen: set[int] = set()
    used = len(outline) + 300
    for index in order:
        cost = len(blocks[index][2]) + 40
        if index not in chosen and used + cost <= limit:
            chosen.add(index)
            used += cost
    body = "\n\n".join(f"[satır {blocks[i][0]}-{blocks[i][1]}]\n{blocks[i][2]}" for i in sorted(chosen))
    note = f"[Not: belge {len(text)} karakter ve {len(blocks)} parça; soruyla en ilgili {len(chosen)} parça aşağıda. Alıntı yaparken satır numarasını belirt; burada olmayan bilgiyi uydurma.]"
    return f"{note}\n\nBAŞLIKLAR:\n{outline}\n\n{body}" if outline else f"{note}\n\n{body}"
