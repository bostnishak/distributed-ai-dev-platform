"""Questions about a whole long document: every part is read, nothing is picked by search alone.

Map: each part yields claims with verbatim quotes. Verify: code keeps quotes that are really in the document and gives
them their line numbers. Reduce: the answer is written from those claims only, behind the same citation gate as research.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import extract
import long_doc
import research
import untrusted

_log = logging.getLogger(__name__)
_WHOLE_RE = re.compile(
    r"tamam[ıi]n[ıi]|tüm\s+(?:belge|döküman|doküman|dosya|metin|rapor|bölüm)|belgenin\s+(?:tamam|bütün|her)|bütün\s+(?:belge|bölüm|dosya)|her\s+bölüm|baştan\s+sona|whole\s+document|entire\s+(?:file|document)",
    re.IGNORECASE,
)
_PART_CHARS = 6000
_MAX_PARTS = 32
_DOC_EXT = (".pdf", ".docx", ".pptx", ".txt", ".md", ".log")


def wants_whole(prompt: str, filename: str, length: int) -> bool:
    return filename.lower().endswith(_DOC_EXT) and length > 2 * _PART_CHARS and bool(_WHOLE_RE.search(prompt))


def parts(text: str) -> list[str]:
    """The document cut into consecutive pieces of about equal size, nothing left out."""
    out: list[str] = []
    for _first, _last, block in long_doc.passages(text):
        if out and len(out[-1]) + len(block) < _PART_CHARS:
            out[-1] += "\n" + block
        else:
            out.append(block)
    return out


def line_of(text: str, quote: str) -> int:
    """1-based line where the quote starts (whitespace differences ignored)."""
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    found = re.search(pattern, text, re.IGNORECASE)
    return text.count("\n", 0, found.start()) + 1 if found else 0


def render(report: research.Report, claims: dict[int, research.Claim], question: str, read: int, total: int) -> str:
    summary, dropped_a = research.gate(report.summary, claims, question)
    details, dropped_b = research.gate(report.details, claims, question)
    out = ["## Yanıt", *([f"- {p.text} {''.join(f'[{i}]' for i in p.ids)}" for p in summary] or ["- Alıntıyla desteklenen bir yanıt çıkmadı; aşağıdaki alıntılara bak."])]
    out += ["", *[f"{p.text} {''.join(f'[{i}]' for i in p.ids)}\n" for p in details]]
    conflicts = [c for c in report.conflicts if len([i for i in c.ids if i in claims]) >= 2]
    if conflicts:
        out += ["## Belgedeki çelişkiler", *[f"- {c.explanation} {''.join(f'[{i}]' for i in c.ids if i in claims)}" for c in conflicts], ""]
    cited = sorted({i for p in (*summary, *details) for i in p.ids} | {i for c in conflicts for i in c.ids if i in claims}) or sorted(claims)
    out += ["## Alıntılar", *[f"[{i}] {claims[i].url}: \"{claims[i].quote}\"" for i in cited]]
    note = f"Belge {total} parçaya bölündü, {read} parçanın tamamı okundu; {len(claims)} alıntı belgede birebir doğrulandı"
    if dropped_a + dropped_b:
        note += f", kanıtsız {dropped_a + dropped_b} cümle silindi"
    return "\n".join([*out, "", f"_{note}._"])


async def answer(question: str, text: str, chat: research.Chat | None = None) -> AsyncIterator[tuple[str, str]]:
    """("status", message) while reading, then one ("report", markdown)."""
    ask = chat or research._ask
    pieces = parts(text)
    used = pieces[:_MAX_PARTS]
    claims: dict[int, research.Claim] = {}
    for index, piece in enumerate(used, start=1):
        yield "status", f"Okunuyor {index}/{len(used)}..."
        found = await research._structured(ask, "agent_research_claims.md", f"SORU: {question}\n\nSAYFA METNİ:\n{untrusted.guard(piece)}", research.Claims)
        for item in research.verified(found.claims if found else [], piece)[:4]:
            line = line_of(text, item.quote)
            if line and all(c.quote != item.quote.strip() for c in claims.values()):
                claims[len(claims) + 1] = research.Claim(len(claims) + 1, item.claim, item.quote.strip(), f"satır {line}", "")
    if not claims:
        yield "report", f"{len(used)} parçanın hepsini okudum; soruyu yanıtlayan, alıntıyla doğrulanabilen bir bilgi bulamadım."
        return
    listing = "\n".join(f"{c.number}. {c.text} (alıntı: \"{c.quote}\", {c.url})" for c in claims.values())[:14000]
    report = await research._structured(ask, "agent_research_report.md", f"SORU: {question}\n\nDOĞRULANMIŞ İDDİALAR:\n{listing}", research.Report)
    report = report or research.Report(summary=[research.Point(text=c.text, ids=[c.number]) for c in list(claims.values())[:8]])
    result = render(report, claims, question, len(used), len(pieces))
    if len(pieces) > len(used):
        result += f"\n\nUYARI: belge çok uzun; son {len(pieces) - len(used)} parça okunmadı."
    yield "report", result


def fastpath(prompt: str, file: UploadFile) -> StreamingResponse | None:
    name = file.filename or ""
    if not name.lower().endswith(_DOC_EXT) or not _WHOLE_RE.search(prompt):
        return None
    raw = file.file.read(20_000_000)
    file.file.seek(0)
    try:
        text = raw.decode("utf-8", "replace") if name.lower().endswith(".log") else extract.extract_text(name, raw)
    except (OSError, ValueError, KeyError, RuntimeError, extract.UnsupportedFileError):
        return None
    if not wants_whole(prompt, name, len(text)):
        return None

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def gen():
        try:
            async for kind, value in answer(prompt, text):
                yield sse({"type": "status", "message": value} if kind == "status" else {"type": "token", "content": value})
        except (OSError, RuntimeError, ValueError) as exc:
            _log.warning("document reading failed: %r", exc)
            yield sse({"type": "error", "content": f"Belge okunamadı: {exc}"})
        yield sse({"type": "done", "model": "doc-reader", "task_type": "dokuman"})

    return StreamingResponse(gen(), media_type="text/event-stream")
