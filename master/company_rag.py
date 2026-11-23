"""Local Company Engineering & CNC Knowledge Base (RAG with bge-m3 embeddings + hybrid keyword search).

Automatically retrieves relevant company CNC standards, ISO 2768/286 tolerances, cutting speeds,
and AS9102 quality rules to ground Assistant responses in real shop-floor engineering data.
"""

from __future__ import annotations

import math
import re
from typing import Any

import httpx

import config

COMPANY_KNOWLEDGE_DOCS: list[dict[str, Any]] = [
    {
        "id": "iso-2768-mk",
        "title": "ISO 2768-mK Genel Tolerans Standardı",
        "keywords": ("iso 2768", "genel tolerans", "tolerans", "lineer", "pah", "radyüs", "mk"),
        "content": (
            "Şirket CNC Standartları - ISO 2768-m (Orta) Lineer Toleranslar: "
            "0.5-3 mm: ±0.1 mm | 3-6 mm: ±0.1 mm | 6-30 mm: ±0.2 mm | 30-120 mm: ±0.3 mm | "
            "120-400 mm: ±0.5 mm | 400-1000 mm: ±0.8 mm. Pah ve radyüslerde 0.5-3 mm: ±0.2 mm, 3-6 mm: ±0.5 mm."
        ),
    },
    {
        "id": "iso-286-fits",
        "title": "ISO 286 Rulman ve Mil-Delik Geçme Toleransları (H7, h6, g6)",
        "keywords": ("h7", "h6", "g6", "h8", "k6", "geçme", "gecme", "rulman", "iso 286", "bara", "rayba"),
        "content": (
            "ISO 286 Hassas Geçmeler: Ø30-50 mm aralığında H7 delik: +0.025 / 0.000 mm; h6 mil: 0.000 / -0.016 mm; "
            "g6 mil: -0.009 / -0.025 mm. Ø50-80 mm aralığında H7: +0.030 / 0 mm; h6: 0 / -0.019 mm. "
            "H7 delikler OP20/OP30'da mikrometrik bara veya H7 karbür rayba ile işlenir ve %100 3 ayaklı iç çap mikrometresi + tampon mastarla ölçülür."
        ),
    },
    {
        "id": "cnc-cutting-speeds",
        "title": "CNC Kesme Hızları (Vc), İlerleme (f) ve Takım Seçim Rehberi",
        "keywords": ("4140", "6061", "7075", "304", "316", "kesme hızı", "kesme hizi", "vc", "ilerleme", "devir", "torna", "freze"),
        "content": (
            "Şirket Tezgâh Kesme Parametreleri: "
            "1) AISI 4140 Islah Çeliği: Torna Vc = 160-210 m/dk, Freze Vc = 120-160 m/dk, f = 0.12-0.25 mm/dev, TiAlN kaplamalı karbür uç. "
            "2) Alüminyum 6061-T6 / 7075: Torna Vc = 350-600 m/dk, Freze Vc = 300-500 m/dk, DLC/parlatılmış pozitif uç. "
            "3) AISI 304/316 Paslanmaz: Torna Vc = 110-150 m/dk, Freze Vc = 80-120 m/dk, yoğun içten soğutma."
        ),
    },
    {
        "id": "as9102-fai-quality",
        "title": "AS9102 İlk Parça Onayı (FAI) ve SPC (Cp/Cpk) Kalite Prosedürü",
        "keywords": ("as9102", "fai", "ilk parça", "kalite", "cmm", "cpk", "spc", "balonlama", "rapor"),
        "content": (
            "AS9102 FAI Prosedürü: Form 1 (Parça Tanımlama), Form 2 (Malzeme 3.1 Sertifikası & Özel Prosesler), "
            "Form 3 (Balonlanmış tüm karakteristiklerin ölçüm tablosu). Kritik ölçülerde (tolerans ≤ 0.05 mm, ISO geçmeler ve GD&T) "
            "%100 CMM ölçümü ve seri üretimde Cp/Cpk ≥ 1.33 şartı aranır."
        ),
    },
    {
        "id": "threads-predrill",
        "title": "Metrik Kılavuz Ön Delik Çapları ve Diş Kontrolü",
        "keywords": ("kılavuz", "kilavuz", "diş", "dis", "vida", "m6", "m8", "m10", "m12", "6h", "ön delik"),
        "content": (
            "Metrik Diş (6H) Ön Delik Standartları: M6x1.0 -> Ø5.0 mm | M8x1.25 -> Ø6.8 mm | "
            "M10x1.5 -> Ø8.5 mm | M12x1.75 -> Ø10.2 mm | M16x2.0 -> Ø14.0 mm. "
            "Tüm dişler HSS-E makine kılavuzu ile çekilir ve 6H Geçer/Geçmez (Go/No-Go) vida mastarı ile %100 kontrol edilir."
        ),
    },
]

_EMBED_CACHE: dict[str, list[float]] = {}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


async def _embed_text(text: str) -> list[float] | None:
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/embeddings",
                json={"model": "bge-m3:latest", "prompt": text},
            )
            if resp.status_code == 200:
                emb = resp.json().get("embedding")
                if isinstance(emb, list) and emb:
                    return emb
    except Exception:
        pass
    return None


def search_company_kb_sync(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Fast lexical/keyword retrieval over the company engineering knowledge base."""
    lower = query.lower()
    tokens = set(re.findall(r"[a-z0-9çğıöşü]+", lower))
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in COMPANY_KNOWLEDGE_DOCS:
        score = 0.0
        for kw in doc["keywords"]:
            if kw in lower:
                score += 3.0
        doc_tokens = set(re.findall(r"[a-z0-9çğıöşü]+", (doc["title"] + " " + doc["content"]).lower()))
        score += len(tokens & doc_tokens) * 0.4
        if score >= 1.5:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]


async def retrieve_company_context(query: str, top_k: int = 2) -> str:
    """Retrieve company CNC/engineering context via hybrid keyword + optional bge-m3 embeddings."""
    lexical = search_company_kb_sync(query, top_k=top_k)
    if not lexical:
        return ""
    # Try bge-m3 semantic re-ranking if query is technical
    q_emb = await _embed_text(query)
    if q_emb:
        reranked: list[tuple[float, dict[str, Any]]] = []
        for doc in COMPANY_KNOWLEDGE_DOCS:
            if doc["id"] not in _EMBED_CACHE:
                d_emb = await _embed_text(doc["title"] + ": " + doc["content"])
                if d_emb:
                    _EMBED_CACHE[doc["id"]] = d_emb
            sim = _cosine(q_emb, _EMBED_CACHE.get(doc["id"], []))
            if sim > 0.35:
                reranked.append((sim, doc))
        if reranked:
            reranked.sort(key=lambda x: x[0], reverse=True)
            lexical = [d for _, d in reranked[:top_k]]

    parts = [f"- [{d['title']}]: {d['content']}" for d in lexical]
    return "\n".join(parts)
