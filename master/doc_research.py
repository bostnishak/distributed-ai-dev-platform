"""Reports, plans and studies get real web research up front and a code-written 'Kaynakça' at the end (never model-invented references)."""

from __future__ import annotations

import asyncio
import re
from typing import Any

_PERSONAL_RE = re.compile(
    r"(sözleşme|sozlesme|dilekçe|dilekce|cv\b|özgeçmiş|ozgecmis|mektup|fatura|tutanak|vekalet|taahhüt|ibraname|makbuz|kira\s+kontrat|"
    r"contract|resume|cover\s+letter|invoice|receipt|agreement)",
    re.IGNORECASE,
)
_TIMEOUT = 75.0
_NO_SOURCES = (
    "\n\nARAŞTIRMA NOTU: Canlı kaynak bulunamadı. Ülke/sektör düzeyinde güncel rakam (kurulu güç, pazar büyüklüğü, fiyat) UYDURMA; "
    "bu tür verileri yazma ya da 'resmi kaynaklardan doğrulanmalıdır' diye işaretle. Yalnızca kullanıcının verdiği sayılar ve açıkça varsayım diye etiketlenen örnek hesaplar kullanılabilir."
)


def wants_research(prompt: str) -> bool:
    """Factual documents (reports, business plans, studies, summaries); not contracts, letters, CVs or forms."""
    return not _PERSONAL_RE.search(prompt or "")


def _facts_note(sources: list[dict[str, str]]) -> str:
    lines = "\n".join(f"- {s['title']} ({s['url']}): {s.get('facts') or s.get('snippet', '')}"[:520] for s in sources)
    return (
        "\n\nARAŞTIRMA BULGULARI (gerçek web kaynakları). Piyasa verisi, oran, fiyat ve olguları mümkünse yalnızca bunlardan al; "
        "bulgularda olmayan rakamı 'varsayım' olarak işaretle. Kaynak listesini kendin yazma (sistem 'Kaynakça' ekler):\n" + lines
    )


async def gather(prompt: str) -> tuple[list[dict[str, str]], str]:
    """(sources, note appended to the request); ([], '') when research does not apply or the web is unreachable."""
    import research_context

    if not wants_research(prompt) or not research_context.web_enabled():
        return [], ""
    try:
        sources, _ = await asyncio.wait_for(asyncio.to_thread(research_context.build, prompt, True), _TIMEOUT)
    except (TimeoutError, OSError, ValueError, RuntimeError):
        return [], _NO_SOURCES
    real = [s for s in sources if str(s.get("url", "")).startswith("http")]
    return real, _facts_note(real) if real else _NO_SOURCES


def bibliography(sources: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Blocks for the closing 'Kaynakça' section."""
    if not sources:
        return []
    items = [f"{s['title'].strip()} — {s['url']}" for s in sources[:6]]
    return [{"type": "heading", "text": "Kaynakça", "level": 1}, {"type": "bullets", "items": items, "own_numbers": False}]
