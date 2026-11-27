"""Deep research with a citation gate.

Plan sub-queries, search, read the pages, take claims with verbatim quotes, and write only from claims whose quote is
really on the page. Code (not the model) drops statements without a valid claim or with a number the quotes do not
contain, and writes the source list. Page text is untrusted data throughout.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

import gateway
import long_doc
import page_facts
import policy
import research_context
import untrusted
from prompt_loader import load_prompt
from rag.web import is_safe_public_url

_log = logging.getLogger(__name__)
_TRIGGER_RE = re.compile(r"derin(?:lemesine)?\s+araştır|deep\s+research|@research|@araştır", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_MODEL = "qwen3.5:9b"
_PAGES_PER_QUERY = 3
_MAX_PAGES = 9
_PAGE_BUDGET = 6000

Chat = Callable[[str, str, dict], Awaitable[str]]


class Plan(BaseModel):
    queries: list[str]


class RawClaim(BaseModel):
    claim: str
    quote: str


class Claims(BaseModel):
    claims: list[RawClaim] = []


class Point(BaseModel):
    text: str
    ids: list[int] = []


class Conflict(BaseModel):
    ids: list[int] = []
    explanation: str = ""


class Report(BaseModel):
    summary: list[Point] = []
    details: list[Point] = []
    conflicts: list[Conflict] = []
    open_questions: list[str] = []


@dataclass(frozen=True)
class Claim:
    number: int
    text: str
    quote: str
    url: str
    title: str


def wants_research(prompt: str) -> bool:
    return bool(_TRIGGER_RE.search(prompt))


async def _ask(system: str, user: str, schema: dict) -> str:
    res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model=_MODEL, profile="extract",
                                            format_schema=schema, num_predict=1600, num_ctx=8192, timeout_s=300.0, feature="research", max_retries=0)
    return res.content


async def _structured(chat: Chat, prompt_file: str, user: str, model: type[BaseModel]) -> BaseModel | None:
    try:
        return model.model_validate_json(await chat(load_prompt(prompt_file), user, model.model_json_schema()))
    except (ValidationError, ValueError, OSError, RuntimeError) as exc:
        _log.warning("research step %s failed: %s", prompt_file, exc)
        return None


def read_page(url: str) -> str:
    """Main text of a public page; '' when unreadable. Redirects to private hosts are refused."""
    if not is_safe_public_url(url)[0]:
        return ""
    try:
        import trafilatura
    except ImportError:
        return page_facts.fetch_text(url)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research reader)", "Accept-Language": "tr,en;q=0.8"})
        with urllib.request.urlopen(request, timeout=10) as resp:
            if not is_safe_public_url(resp.geturl())[0] or "html" not in resp.headers.get("Content-Type", "html"):
                return ""
            raw = resp.read(900_000).decode(resp.headers.get_content_charset() or "utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError, LookupError):
        return ""
    return trafilatura.extract(raw, include_tables=True, include_comments=False) or ""


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _canonical(number: str) -> str:
    """One spelling per value: "480.000", "480,000" and "480000" are the same; "3,5" and "3.5" are the same."""
    number = number.rstrip(".,")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", number):
        number = number.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", number):
        number = number.replace(",", "")
    return number.replace(",", ".")


def _numbers(text: str) -> set[str]:
    return {_canonical(n) for n in _NUMBER_RE.findall(text)}


def verified(raw: list[RawClaim], page: str) -> list[RawClaim]:
    """Claims whose quote is literally on the page and covers every number the claim states."""
    body = _flat(page)
    return [c for c in raw if len(c.quote) >= 20 and _flat(c.quote) in body and _numbers(c.claim) <= _numbers(c.quote)]


def gate(points: list[Point], claims: dict[int, Claim], question: str) -> tuple[list[Point], int]:
    """(statements backed by real claims, how many were dropped)."""
    kept: list[Point] = []
    for point in points:
        ids = [i for i in point.ids if i in claims]
        text = re.sub(r"\s*\[\d+(?:\s*,\s*\d+)*\]", "", point.text).strip()
        allowed = _numbers(question).union(*(_numbers(claims[i].quote) for i in ids)) if ids else set()
        if ids and text and _numbers(text) <= allowed:
            kept.append(Point(text=text, ids=ids))
    return kept, len(points) - len(kept)


def _cite(point: Point) -> str:
    return f"{point.text} {''.join(f'[{i}]' for i in point.ids)}"


def render(report: Report, claims: dict[int, Claim], question: str, read: int) -> str:
    summary, dropped_a = gate(report.summary, claims, question)
    details, dropped_b = gate(report.details, claims, question)
    out = ["## Özet", *([f"- {_cite(p)}" for p in summary] or ["- Doğrulanmış kanıtla desteklenen bir özet çıkmadı; aşağıdaki alıntılara bak."])]
    if details:
        out += ["", "## Ayrıntılar", *[_cite(p) + "\n" for p in details]]
    conflicts = [c for c in report.conflicts if len([i for i in c.ids if i in claims]) >= 2]
    if conflicts:
        out += ["", "## Çelişen bilgiler", *[f"- {c.explanation} {''.join(f'[{i}]' for i in c.ids if i in claims)}" for c in conflicts]]
    if report.open_questions:
        out += ["", "## Yanıtlanamayanlar", *[f"- {q}" for q in report.open_questions[:5]]]
    cited = sorted({i for p in (*summary, *details) for i in p.ids}) or sorted(claims)
    out += ["", "## Kanıtlar"]
    out += [f"[{i}] [{claims[i].title or claims[i].url}]({claims[i].url}): \"{claims[i].quote}\"" for i in cited]
    note = f"{read} sayfa okundu, {len(claims)} iddia sayfadaki birebir alıntıyla doğrulandı"
    if dropped_a + dropped_b:
        note += f", kanıtsız kalan {dropped_a + dropped_b} cümle silindi"
    return "\n".join([*out, "", f"_{note}. Alıntının sayfada olması, sayfanın doğru söylediği anlamına gelmez._"])


async def _gather(queries: list[str], run: policy.Context) -> list[tuple[str, str, str]]:
    """(url, title, text) of the pages found for the queries."""
    found: dict[str, str] = {}
    for query in queries:
        if not policy.check("web_search", integrity=run.integrity, payload=query).allowed:
            continue
        for hit in (await asyncio.to_thread(research_context.web_search, query, 6))[:_PAGES_PER_QUERY]:
            found.setdefault(hit["url"], hit["title"])
    urls = list(found)[:_MAX_PAGES]
    texts = await asyncio.gather(*(asyncio.to_thread(read_page, u) for u in urls))
    run.read_external()
    return [(u, found[u], t) for u, t in zip(urls, texts, strict=True) if len(t) > 200]


async def _read(pages: list[tuple[str, str, str]], question: str, chat: Chat, claims: dict[int, Claim]) -> AsyncIterator[tuple[str, str]]:
    """Extract verified claims from each page into `claims`."""
    for index, (url, title, text) in enumerate(pages, start=1):
        yield "status", f"Okunuyor {index}/{len(pages)}: {title[:70]}"
        passage = untrusted.guard(long_doc.select(text, question, _PAGE_BUDGET))
        found = await _structured(chat, "agent_research_claims.md", f"SORU: {question}\n\nSAYFA METNİ:\n{passage}", Claims)
        for item in verified(found.claims if found else [], text)[:4]:
            claims[len(claims) + 1] = Claim(len(claims) + 1, item.claim, item.quote.strip(), url, title[:90])


async def _write_report(question: str, claims: dict[int, Claim], chat: Chat) -> Report:
    listing = "\n".join(f"{c.number}. {c.text} (alıntı: \"{c.quote}\") — {c.url}" for c in claims.values())
    report = await _structured(chat, "agent_research_report.md", f"SORU: {question}\n\nDOĞRULANMIŞ İDDİALAR:\n{listing}", Report)
    return report or Report(summary=[Point(text=c.text, ids=[c.number]) for c in list(claims.values())[:6]])


async def investigate(question: str, chat: Chat = _ask) -> AsyncIterator[tuple[str, str]]:
    """("status", message) while working, then one ("report", markdown). Unanswered points get a second search round."""
    question = _TRIGGER_RE.sub(" ", question).strip(" :,-") or question
    if not research_context.web_enabled():
        yield "report", "Web araması kapalı olduğu için araştırma yapamıyorum; güncel olmayan bilgiyi araştırma sonucu gibi sunmuyorum."
        return
    yield "status", "Araştırma planı hazırlanıyor..."
    plan = await _structured(chat, "agent_research_plan.md", question, Plan)
    queries = [q for q in (plan.queries if plan else []) if q.strip()][:4] or [question]
    yield "status", "Aranıyor: " + " | ".join(queries)
    run = policy.Context()
    pages = await _gather(queries, run)
    claims: dict[int, Claim] = {}
    async for event in _read(pages, question, chat, claims):
        yield event
    if not claims:
        yield "report", f"{len(pages)} sayfa okundu ama soruyu yanıtlayan, alıntıyla doğrulanabilen bir bilgi bulamadım. Soruyu daha dar sorabilirsin."
        return
    yield "status", f"{len(claims)} doğrulanmış iddiadan rapor yazılıyor..."
    report = await _write_report(question, claims, chat)
    total = len(pages)
    if gaps := [q for q in report.open_questions if q.strip()][:2]:
        yield "status", "İkinci tur, yanıtsız kalanlar: " + " | ".join(gaps)
        seen = {url for url, _t, _x in pages}
        # queries are built from model output over web text: they pass the same egress check as the first round
        extra = [p for p in await _gather(gaps, run) if p[0] not in seen][:4]
        before = len(claims)
        async for event in _read(extra, question, chat, claims):
            yield event
        total += len(extra)
        if len(claims) > before:
            report = await _write_report(question, claims, chat)
    yield "report", render(report, claims, question, total)


def fastpath(prompt: str, has_file: bool) -> StreamingResponse | None:
    """SSE research run when the user asks for deep research; None otherwise."""
    if has_file or not wants_research(prompt):
        return None

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def gen():
        async for kind, text in investigate(prompt):
            yield sse({"type": "status", "message": text} if kind == "status" else {"type": "token", "content": text})
        yield sse({"type": "done", "model": "deep-research", "task_type": "arastirma"})

    return StreamingResponse(gen(), media_type="text/event-stream")
