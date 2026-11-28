"""`inbox`: drop a scanned PDF, a messy spreadsheet or a recording there and ask about it; every claim cites its place.

Each file becomes a list of sources with a locator (page and box, sheet and cell row, or time in the recording). The
model answers only from the retrieved sources and must cite them; a citation that does not exist, or a number that no
cited source contains, is rejected.

  inbox                    lists what is in the folder
  inbox: <soru>            answers from the files, with places
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
from fastapi.responses import StreamingResponse

import config
import extract
import ingest_pdf
import media_index
import sheet_infer
import turkish
from prompt_loader import load_prompt

_COMMAND_RE = re.compile(r"^\s*inbox\s*(?::\s*(?P<question>.+))?\s*$", re.IGNORECASE | re.DOTALL)
_CITE_RE = re.compile(r"\[(\d{1,3})\]")
_NUMBER_RE = re.compile(r"\d[\d.,]*\d|\d")
_SUPPORTED = (".pdf", ".xlsx", ".xlsm", ".csv", ".tsv", ".docx", ".pptx", ".txt", ".md", ".png", ".jpg", ".jpeg", *media_index.AUDIO)
_MAX_BYTES = 200 * 1024 * 1024
_TOP = 12
_log = logging.getLogger(__name__)

Generate = Callable[[str, str], Awaitable[str]]


@dataclass(frozen=True)
class Source:
    file: str
    place: str
    text: str

    def label(self) -> str:
        return f"{self.file}, {self.place}"


def folder() -> Path:
    path = config.data_dir() / "inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def files() -> list[Path]:
    return sorted(p for p in folder().iterdir() if p.is_file() and p.suffix.lower() in _SUPPORTED and p.stat().st_size <= _MAX_BYTES)


def _pdf(path: Path) -> list[tuple[str, str]]:
    found, warnings = ingest_pdf.blocks(path.read_bytes())
    pages = [(f"sayfa {b.page} ({'OCR, ' if b.kind == 'ocr' else ''}kutu {', '.join(str(int(v)) for v in b.box)})", b.text) for b in found]
    return pages + [("uyarı", w) for w in warnings]


def _sheet(path: Path) -> list[tuple[str, str]]:
    tables = sheet_infer.from_xlsx(path.read_bytes()) if path.suffix.lower() in (".xlsx", ".xlsm") else sheet_infer.from_csv(extract._decode_bytes(path.read_bytes()))
    rows = []
    for table in tables:
        for number, row in zip(table.row_numbers, table.rows, strict=True):
            rows.append((f"{table.sheet} satır {number}", "; ".join(f"{name}={sheet_infer._shown(v)}" for name, v in zip(table.header, row, strict=True))))
        for column, name in enumerate(table.header):
            if table.types[column] == "sayı":
                values = [row[column] for row in table.rows if row[column] is not None]
                rows.append((f"{table.sheet} sütun {table.columns[column]} (kodla hesaplandı)", f"{name} toplamı={format(sum(values), 'f')}; en büyük={format(max(values), 'f')}; en küçük={format(min(values), 'f')}; adet={len(values)}"))
    return rows


def _recording(path: Path) -> list[tuple[str, str]]:
    rows = [(f"{media_index.clock(s.start)}-{media_index.clock(s.end)}", s.text) for s in media_index.transcribe(path)]
    if path.suffix.lower() in media_index.VIDEO:
        frames = media_index.keyframes(path, folder().parent / "inbox_frames")
        rows += [(media_index.clock(moment), f"sahne değişimi karesi: {name}") for moment, name in frames]
    return rows


def _image(path: Path) -> list[tuple[str, str]]:
    import ocr_engine

    return [(f"görüntü kutusu {', '.join(str(int(v)) for v in line.box)}", line.text) for line in ocr_engine.read(path.read_bytes())]


def _plain(path: Path) -> list[tuple[str, str]]:
    text = extract.extract_text(path.name, path.read_bytes())
    return [(f"paragraf {number}", part.strip()) for number, part in enumerate(re.split(r"\n\s*\n|\n", text), 1) if part.strip()]


def _reader(path: Path) -> Callable[[Path], list[tuple[str, str]]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf
    if suffix in (".xlsx", ".xlsm", ".csv", ".tsv"):
        return _sheet
    if suffix in media_index.AUDIO:
        return _recording
    return _image if suffix in (".png", ".jpg", ".jpeg") else _plain


def sources_of(path: Path) -> list[Source]:
    """The located pieces of one file; read once, then kept until the file changes."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    cache = config.data_dir() / "inbox_index" / f"{digest}.json"
    if cache.is_file():
        return [Source(path.name, place, text) for place, text in json.loads(cache.read_text(encoding="utf-8"))]
    try:
        rows = _reader(path)(path)
    except Exception as exc:  # noqa: BLE001, RUF100  # one unreadable file must not hide the others; it is reported as a source
        _log.warning("inbox dosyası okunamadı (%s): %s", path.name, exc)
        return [Source(path.name, "uyarı", f"okunamadı: {type(exc).__name__}: {str(exc)[:160]}")]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return [Source(path.name, place, text) for place, text in rows]


def _stems(text: str) -> set[str]:
    return {word[:5] for word in re.findall(r"[^\W_]{3,}", turkish.lower(text))}


def retrieve(question: str, sources: list[Source], top: int = _TOP) -> list[Source]:
    """The pieces sharing the most word stems with the question; computed totals travel with their table's rows."""
    wanted = _stems(question)
    scored = sorted(((len(wanted & _stems(f"{s.file} {s.place} {s.text}")), -index, s) for index, s in enumerate(sources)), key=lambda x: (x[0], x[1]), reverse=True)
    picked = [s for score, _i, s in scored if score][:top]
    totals = [s for s in sources if "kodla hesaplandı" in s.place and any(s.file == p.file for p in picked) and s not in picked]
    return (picked + totals) if picked else sources[:top]


def _values(text: str) -> set[Decimal]:
    """Every number of a text as a value, whichever way it is written."""
    found: set[Decimal] = set()
    for token in _NUMBER_RE.findall(text):
        turkish_style = token.replace(".", "").replace(",", ".")
        american = token.replace(",", "")
        for candidate in (turkish_style, american):
            try:
                found.add(Decimal(candidate).normalize())
            except InvalidOperation:
                continue
    return found


def problems(answer: str, given: list[Source]) -> list[str]:
    """Why an answer cannot be trusted: no citation, a citation that does not exist, a number its sources lack."""
    cited = [int(n) for n in _CITE_RE.findall(answer)]
    if not cited:
        return [] if "bulamadım" in answer.lower() else ["hiç kaynak gösterilmedi"]
    if missing := sorted({n for n in cited if not 1 <= n <= len(given)}):
        return [f"olmayan kaynak numarası: {missing}"]
    backing = _values(" ".join(f"{given[n - 1].text} {given[n - 1].place}" for n in cited))
    claimed = _values(_CITE_RE.sub("", re.sub(r"(?m)^\s*\d+[.)]\s", "", answer)))
    stray = [format(v, "f") for v in claimed - backing]
    return [f"kaynaklarda olmayan sayı: {', '.join(stray[:4])}"] if stray else []


async def answer(question: str, generate: Generate) -> str:
    everything = await asyncio.to_thread(lambda: [source for path in files() for source in sources_of(path)])
    if not everything:
        return f"Inbox boş. Dosyaları buraya bırak: `{folder()}`"
    given = retrieve(question, everything)
    listed = "\n".join(f"[{n}] ({s.label()}) {s.text}" for n, s in enumerate(given, 1))
    ask = f"SORU: {question}\n\nKAYNAKLAR:\n{listed}"
    reply, found = "", ["yanıt üretilemedi"]
    for _attempt in range(2):
        reply = (await generate(load_prompt("inbox_answer.txt"), ask)).strip()
        found = problems(reply, given)
        if not found:
            break
        ask += f"\n\nÖNCEKİ YANITIN REDDEDİLDİ: {'; '.join(found)}. Yalnız kaynaklardaki bilgiyle ve kaynak numarasıyla yeniden yanıtla."
    cited = sorted({int(n) for n in _CITE_RE.findall(reply) if 1 <= int(n) <= len(given)})
    if found:
        shown = "\n".join(f"- {s.label()}: {s.text}" for s in given[:6])
        return f"Doğrulanabilir bir yanıt üretemedim ({'; '.join(found)}). En ilgili kaynaklar:\n{shown}"
    return reply + ("\n\n**Kaynaklar**\n" + "\n".join(f"[{n}] {given[n - 1].label()}" for n in cited) if cited else "")


def listing() -> str:
    found = files()
    if not found:
        return f"Inbox boş. Taranmış PDF, Excel/CSV, ses ya da video dosyalarını buraya bırak: `{folder()}`"
    return "Inbox:\n" + "\n".join(f"- {p.name} ({p.stat().st_size / 1024:.0f} KB)" for p in found) + "\n\nSoru için: `inbox: <sorun>`"


def question_of(prompt: str) -> str | None:
    """None: not an inbox command; "": list the folder."""
    match = _COMMAND_RE.match(prompt)
    return (match["question"] or "").strip() if match else None


async def _generate(system: str, user: str) -> str:
    import gateway

    reply = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], profile="factual", model="qwen3.5:9b",
                                              num_predict=900, num_ctx=8192, timeout_s=420.0, feature="inbox", max_retries=0)
    return reply.content


async def _stream(question: str) -> AsyncIterator[str]:
    import assistant_stream_fastpaths as fp

    try:
        if question:
            yield fp.sse_event({"type": "status", "message": "Inbox dosyaları okunuyor..."})
            text = await answer(question, _generate)  # file reading happens off the event loop inside
        else:
            text = await asyncio.to_thread(listing)
        yield fp.sse_event({"type": "token", "content": text})
        yield fp.sse_event({"type": "done", "model": "inbox", "task_type": "analiz"})
    except (httpx.HTTPError, OSError, ValueError, RuntimeError) as exc:
        yield fp.sse_event({"type": "error", "content": f"Inbox okunamadı: {exc}"})


def fastpath(prompt: str) -> StreamingResponse | None:
    question = question_of(prompt)
    return None if question is None else StreamingResponse(_stream(question), media_type="text/event-stream")
