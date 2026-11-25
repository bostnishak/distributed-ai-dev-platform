"""Let the model think before answering puzzles, proofs and multi-step calculations (slower, far fewer wrong answers)."""

from __future__ import annotations

import os
import re
from contextvars import ContextVar

THINK: ContextVar[bool] = ContextVar("think_before_answering", default=False)
_RE = re.compile(
    r"(bulmaca|bilmece|puzzle|riddle|paradoks|paradox|kanıtla|ispat\w*|prove\b|olasıl\w*|probability|how\s+many\s+ways|kaç\s+farklı|kaç\s+yolla|"
    r"permütasyon|kombinasyon|sudoku|yalancı|şövalye|knights?\s+and\s+knaves|hangi\s+kutu|etiket\w*\s+(?:de\s+)?yanlış|labels?\s+are\s+(?:all\s+)?wrong|"
    r"en\s+az\s+kaç\s+(?:hamle|adım|deneme)|minimum\s+number\s+of\s+(?:moves|steps|weighings))",
    re.IGNORECASE,
)
_NOT_PUZZLE_RE = re.compile(r"\b(python|kod|fonksiyon|sql|html|excel|word|pdf|sunum|belge|dosya|logo|resim|proje|web\s*sitesi|script|code|function)\b", re.IGNORECASE)
_WORD_PROBLEM_RE = re.compile(r"(kaç\b|how\s+many|how\s+much|ne\s+kadar\s+sürer|kaç\s+(?:yaşında|gün|saat|dakika|km|lira|tl))", re.IGNORECASE)


def needs_thinking(prompt: str) -> bool:
    """Hard logic / probability / counting / multi-step arithmetic questions (not code, documents or everyday chat)."""
    text = (prompt or "").strip()
    if len(text) < 25 or len(text) > 700 or _NOT_PUZZLE_RE.search(text):
        return False
    if _RE.search(text):
        return True
    return len(re.findall(r"\d+(?:[.,]\d+)?", text)) >= 3 and bool(_WORD_PROBLEM_RE.search(text)) and text.endswith("?")


def mark(prompt: str) -> None:
    """Raw thinking tokens are opt-in (REASONING_THINK=1): this model can think for 6000+ tokens and never answer. Puzzles go through solve() instead."""
    THINK.set(needs_thinking(prompt) and os.environ.get("REASONING_THINK", "0") == "1")


def guidance(prompt: str) -> str:
    """System note for puzzle/proof/multi-step questions: a short plan, then one clean answer (no rambling or self-contradiction)."""
    if not needs_thinking(prompt):
        return ""
    return (
        "MANTIK/ÇÖZÜM SORUSU KURALLARI: Önce çözümü kendi içinde doğru kur, sonra yalnızca net sonucu yaz. En fazla 6 numaralı adım kullan, "
        "her adım tek cümle olsun. Aynı şeyi tekrar etme, 'ancak/aslında/peki' diyerek kendini düzeltme; emin olmadığın bir adımı yazma. "
        "Son satırda tek cümlelik kesin sonucu ver."
    )


_JUDGE = (
    "Aşağıda bir mantık/hesap sorusu ve üç aday çözüm var. Soruyu kendin de baştan çöz, adayları karşılaştır ve hatalı olanları ele. "
    "Ardından DOĞRU çözümü yaz: en fazla 6 numaralı kısa adım, sonra tek cümlelik kesin sonuç. Adaylar çelişiyorsa mantığı adım adım doğrulayarak karar ver. "
    "Aday ya da yargıç olduğunu belirtme, aynı şeyi tekrar etme, sadece nihai çözümü yaz."
)


REASONER = "deepseek-r1:8b"


async def _chat(model: str, messages: tuple[str, str], budget: tuple[int, float], think: bool = False) -> str:
    """One non-streaming Ollama chat."""
    from gateway import raw_chat

    return await raw_chat.chat(model, messages, budget, think)


async def reasoner_installed() -> bool:
    import httpx

    import config

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            tags = (await client.get(f"{config.OLLAMA_URL}/api/tags")).json().get("models", [])
    except (httpx.HTTPError, OSError, ValueError):
        return False
    return any(str(m.get("name", "")).startswith(REASONER.split(":")[0]) for m in tags)


_EN_WORDS = frozenset("the and is are if then box boxes label labeled that this which because so you your draw from only contains contain will be it of to in".split())


def _english_ratio(text: str) -> float:
    """Share of English function words in a text: high means a 'Turkish' answer is really English or a mixture."""
    words = re.findall(r"[A-Za-zçğıöşüÇĞİÖŞÜ]+", text.lower())
    return sum(w in _EN_WORDS for w in words) / len(words) if words else 1.0


async def solve_deep(prompt: str, general_model: str) -> str:
    """Translate to English, let the reasoning model think (it is far stronger in English), translate the verified solution back."""
    english_q = await _chat(general_model, ("Translate the user's question into precise English. Return only the translation.", prompt), (700, 120.0))
    solution = await _chat(REASONER, ("", english_q + "\n\nGive only the verified final answer: at most 5 short numbered steps that are consistent with your own reasoning (no doubts, no corrections, no repeated cases), then a conclusion that covers every case."), (3500, 240.0), think=True)
    if not solution:
        return ""
    ask = "Translate this solution into Turkish. Keep every sentence's meaning exactly; do not solve, reorder or change anything. Output only Turkish:\n\n" + solution
    turkish = await _chat(REASONER, ("", ask), (2500, 150.0))
    if _english_ratio(turkish) > 0.06:  # the reasoner drifted back into English: translate again with the general model
        turkish = await _chat(general_model, ("Translate into Turkish. Return only Turkish.", solution), (1400, 240.0))
    return turkish if _english_ratio(turkish) <= 0.06 else ""


async def solve(prompt: str) -> str:
    """Three independent concise solutions, then a judge pass that verifies them and writes the final answer; '' on failure."""
    import asyncio

    import gateway
    import multimodal_studio as mms

    model = await mms.pick_best_model("deep")
    if await reasoner_installed():
        try:
            if deep := await solve_deep(prompt, model):
                return deep
        except (OSError, RuntimeError, ValueError, TypeError):
            pass  # fall back to the self-consistency solver below
    system = {"role": "system", "content": guidance(prompt)}

    async def one(temp_seed: int) -> str:
        res = await gateway.default_client.chat([system, {"role": "user", "content": prompt}], model=model, profile="analytic", num_predict=900, timeout_s=240.0, feature="reasoning", seed=temp_seed, max_retries=0)
        return res.content.strip()

    try:
        drafts = [d for d in await asyncio.gather(*(one(s) for s in (11, 22, 33)), return_exceptions=True) if isinstance(d, str) and d]
        if not drafts:
            return ""
        candidates = "\n\n".join(f"ADAY {i}:\n{d}" for i, d in enumerate(drafts, 1))
        ask = f"SORU:\n{prompt}\n\n{candidates}"
        res = await gateway.default_client.chat([{"role": "system", "content": _JUDGE}, {"role": "user", "content": ask}], model=model, profile="factual", num_predict=1100, timeout_s=300.0, feature="reasoning", max_retries=0)
    except (OSError, RuntimeError, ValueError, TypeError):
        return ""
    return res.content.strip()


async def fastpath(prompt: str, has_file: bool) -> object:
    """SSE response for a puzzle/proof question: a status line, then the verified solution; None for anything else."""
    if has_file or not needs_thinking(prompt):
        return None
    import json

    from fastapi.responses import StreamingResponse

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def gen():
        yield sse({"type": "status", "message": "Zor bir mantık sorusu: derin akıl yürütme modeliyle çözülüyor, birkaç dakika sürebilir..."})
        answer = await solve(prompt)
        yield sse({"type": "token", "content": answer or "Bu soruyu güvenilir biçimde çözemedim; soruyu biraz daha ayrıntılı yazarsan tekrar deneyeyim."})
        yield sse({"type": "done", "model": "reasoning-verified", "task_type": "genel"})

    return StreamingResponse(gen(), media_type="text/event-stream")
