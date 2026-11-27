"""Questions about a whole long document: every part is read, nothing is picked by search alone.

Map: each part yields claims with verbatim quotes. Verify: code keeps quotes that are really in the document and gives
them their line numbers. Reduce: the answer is written from those claims only, behind the same citation gate as research.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from collections import Counter
from collections.abc import AsyncIterator

import pymupdf
from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import exact_cache
import extract
import long_doc
import research
import semantic_cache
import turkish
import untrusted

_log = logging.getLogger(__name__)
_WHOLE_RE = re.compile(
    r"tamam[ıi]n[ıi]|tüm\s+(?:belge|döküman|doküman|dosya|metin|rapor|bölüm)|belgenin\s+(?:tamam|bütün|her)|bütün\s+(?:belge|bölüm|dosya)|her\s+bölüm|baştan\s+sona|whole\s+document|entire\s+(?:file|document)",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(r"\bözetle|\bözet\s+(?:çıkar|ver|yaz)|\bsummar", re.IGNORECASE)
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


def select(pieces: list[str], question: str, limit: int = _MAX_PARTS) -> tuple[list[str], bool]:
    """All parts when they fit the budget; otherwise the ones that share the question's rarest words, in document order."""
    if len(pieces) <= limit:
        return pieces, False
    wanted = {w[:5] for w in re.findall(r"\w{4,}", question.casefold())}
    seen = [{w[:5] for w in re.findall(r"\w{4,}", p.casefold())} for p in pieces]
    rarity = {w: math.log(1 + len(pieces) / (1 + sum(w in s for s in seen))) for w in wanted}
    ranked = sorted(range(len(pieces)), key=lambda i: (-sum(rarity[w] for w in wanted & seen[i]), i))[:limit]
    return [pieces[i] for i in sorted(ranked)], True


def pdf_pages(name: str, raw: bytes) -> list[str]:
    """Text of each page of a PDF ([] for other files), so a quote can be cited by page."""
    if not name.lower().endswith(".pdf"):
        return []
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        return [" ".join(page.get_text("text").split()).casefold() for page in doc]


def place(text: str, pages: list[str], quote: str) -> str:
    """"sayfa N" or "satır N" of a quote; '' when it is not in the document."""
    line = line_of(text, quote)
    if not line:
        return ""
    needle = " ".join(quote.split()).casefold()
    return next((f"sayfa {n}" for n, page in enumerate(pages, 1) if needle in page), f"satır {line}")


def line_of(text: str, quote: str) -> int:
    """1-based line where the quote starts (whitespace differences ignored)."""
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    found = re.search(pattern, text, re.IGNORECASE)
    return text.count("\n", 0, found.start()) + 1 if found else 0


_ASKING = {"belge", "tamam", "nedir", "kaçtı", "hangi", "göre", "bakın", "oku", "özet"}


def sweep(text: str, question: str, limit: int = 8) -> list[str]:
    """Sentences with a figure that share at least two of the question's rare words: they must not depend on the model noticing them."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])|\n", text) if s.strip()]
    wanted = {w[:5] for w in re.findall(r"\w{4,}", turkish.lower(question))} - _ASKING
    seen: Counter[str] = Counter()
    stems = []
    for sentence in sentences:
        found = {w[:5] for w in re.findall(r"\w{4,}", turkish.lower(sentence))} & wanted
        stems.append(found)
        seen.update(found)
    rare = {w for w in wanted if 0 < seen[w] <= max(3, len(sentences) // 200)}
    hits = [(len(found & rare), index) for index, (sentence, found) in enumerate(zip(sentences, stems, strict=True))
            if len(found & rare) >= 2 and re.search(r"\d", sentence) and 20 <= len(sentence) <= 400]
    out: list[str] = []
    for _score, index in sorted(hits, key=lambda h: (-h[0], h[1])):
        if sentences[index] not in out:
            out.append(sentences[index])
    return out[:limit]


def add_swept(claims: dict[int, research.Claim], text: str, question: str, pages: list[str]) -> list[int]:
    """Add the swept sentences the model did not quote; returns their numbers."""
    added = []
    for sentence in sweep(text, question):
        quoted = " ".join(sentence.split())
        if any(quoted in " ".join(c.quote.split()) or " ".join(c.quote.split()) in quoted for c in claims.values()):
            continue
        if where := place(text, pages, sentence):
            number = len(claims) + 1
            claims[number] = research.Claim(number, sentence, sentence, where, "")
            added.append(number)
    return added


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


async def answer(question: str, text: str, chat: research.Chat | None = None, pages: list[str] | None = None) -> AsyncIterator[tuple[str, str]]:
    """("status", message) while reading, then one ("report", markdown)."""
    ask = chat or exact_cache.cached(research._ask, research._MODEL)
    pieces = parts(text)
    used, selected = select(pieces, question)
    claims: dict[int, research.Claim] = {}
    for index, piece in enumerate(used, start=1):
        yield "status", f"Okunuyor {index}/{len(used)}..."
        found = await research._structured(ask, "agent_research_claims.md", f"SORU: {question}\n\nSAYFA METNİ:\n{untrusted.guard(piece)}", research.Claims)
        for item in research.verified(found.claims if found else [], piece)[:4]:
            where = place(text, pages or [], item.quote)
            if where and all(c.quote != item.quote.strip() for c in claims.values()):
                claims[len(claims) + 1] = research.Claim(len(claims) + 1, item.claim, item.quote.strip(), where, "")
    swept = add_swept(claims, text, question, pages or [])
    if not claims:
        yield "report", f"{len(pieces)} parçalık belgenin {len(used)} parçasını okudum; soruyu yanıtlayan, alıntıyla doğrulanabilen bir bilgi bulamadım."
        return
    listing = "\n".join(f"{c.number}. {c.text} (alıntı: \"{c.quote}\", {c.url})" for c in claims.values())[:14000]
    report = await research._structured(ask, "agent_research_report.md", f"SORU: {question}\n\nDOĞRULANMIŞ İDDİALAR:\n{listing}", research.Report)
    report = report or research.Report(summary=[research.Point(text=c.text, ids=[c.number]) for c in list(claims.values())[:8]])
    cited = {i for p in (*report.summary, *report.details) for i in p.ids}
    report.summary += [research.Point(text=claims[i].text, ids=[i]) for i in swept if i not in cited]
    result = render(report, claims, question, len(used), len(pieces))
    if selected:
        result += f"\n\nUYARI: belge çok uzun; {len(pieces)} parçadan soruyla en ilgili {len(used)} tanesi okundu, diğerleri okunmadı."
    yield "report", result


def fastpath(prompt: str, file: UploadFile) -> StreamingResponse | None:
    name = file.filename or ""
    if not name.lower().endswith(_DOC_EXT) or not _WHOLE_RE.search(prompt):
        return None
    import doc_tree  # doc_tree builds on this module

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
            if earlier := await asyncio.to_thread(semantic_cache.lookup, text, prompt):
                yield sse({"type": "token", "content": earlier + "\n\n_Bu belge değişmediği için aynı sorunun önceki yanıtı gösterildi._"})
                yield sse({"type": "done", "model": "doc-reader", "task_type": "dokuman"})
                return
            reader = doc_tree.summarise(text) if _SUMMARY_RE.search(prompt) else answer(prompt, text, pages=pdf_pages(name, raw))
            async for kind, value in reader:
                if kind == "report" and "alıntı" in value.casefold():
                    await asyncio.to_thread(semantic_cache.store, text, prompt, value)
                yield sse({"type": "status", "message": value} if kind == "status" else {"type": "token", "content": value})
        except (OSError, RuntimeError, ValueError) as exc:
            _log.warning("document reading failed: %r", exc)
            yield sse({"type": "error", "content": f"Belge okunamadı: {exc}"})
        yield sse({"type": "done", "model": "doc-reader", "task_type": "dokuman"})

    return StreamingResponse(gen(), media_type="text/event-stream")
