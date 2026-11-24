"""EPK-20: Curated Local Cited Legal, Health & Finance KBs with Mandatory Disclaimer & 112 Emergency Guard."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/domains/kb", tags=["domains-curated-kb"])

_KB_PATH = Path(__file__).resolve().parent / "kb" / "curated_tr_kb.json"
_EMERGENCY_CUES = (
    "göğüs ağrısı", "gogus agrisi", "nefes alamıyorum", "nefes alamiyorum", "felç", "felc",
    "intihar", "kendime zarar", "kalp krizi", "şiddetli kanama", "siddetli kanama",
)
_DISCLAIMERS: dict[str, str] = {
    "legal": "Yasal Uyarı: Bu çıktı genel mevzuat bilgilendirmesidir; hukuki danışmanlık veya avukat görüşü yerine geçmez.",
    "health": "Tıbbi Uyarı: Bu bilgi yalnızca genel sağlık bilgilendirmesidir; tanı ve tedavi için hekime başvurun.",
    "finance": "Finansal Uyarı: Bu bilgiler yatırım tavsiyesi (SPK kapsamında danışmanlık) değildir.",
}


@lru_cache(maxsize=2)
def _load_kb() -> dict[str, list[dict[str, Any]]]:
    return json.loads(_KB_PATH.read_text(encoding="utf-8"))


def query_curated_domain_kb(domain: str, query: str) -> dict[str, Any]:
    """Query local vetted legal/health/finance KB with mandatory citations, disclaimer, and 112 emergency guard."""
    dom = domain.strip().lower()
    if dom not in _DISCLAIMERS:
        raise ValueError("Desteklenen alanlar: legal, health, finance.")
    low = (query or "").lower()
    emergency = dom == "health" and any(cue in low for cue in _EMERGENCY_CUES)
    entries = _load_kb().get(dom, [])
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in entries:
        hits = sum(1 for kw in item.get("keywords", []) if kw in low)
        if hits > 0:
            scored.append((hits, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    matched = [item for _, item in scored] or entries[:1]
    citations = [{"code": m["id"], "title": m["title"], "excerpt": m["text"]} for m in matched]
    return {
        "ok": True,
        "domain": dom,
        "emergency_redirect": emergency,
        "emergency_message": "ACİL DURUM: Lütfen derhal 112 Acil Yardım hattını arayın veya en yakın acil servise başvurun." if emergency else "",
        "disclaimer": _DISCLAIMERS[dom],
        "citation_count": len(citations),
        "citations": citations,
    }


class DomainKbQueryRequest(BaseModel):
    domain: str = Field(..., pattern="^(legal|health|finance)$")
    query: str = Field(..., min_length=2, max_length=1000)


@router.post("/query")
async def api_query_domain_kb(body: DomainKbQueryRequest):
    """Query curated Turkish legal/health/finance KB with mandatory citation & emergency guard."""
    try:
        return query_curated_domain_kb(body.domain, body.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
