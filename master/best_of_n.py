"""For a decision that is expensive to reverse: write several designs, score them, then recommend one.

"en iyi 3 seçenek: <karar>" (or "mimari seçenekler: ..."). Each candidate is written with a different priority, with
its trade-offs. The score is a fixed rubric (does it cover the question's terms, does it say what happens on failure,
does it name risks) plus a separate critic pass on four axes. Numbers and the winner are computed by code.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from fastapi.responses import StreamingResponse

import chat_stream
import judge
import workspace_builder as wb

_ASK_RE = re.compile(r"^\s*(?:en\s+iyi\s+(?P<n>[23])(?:\s+(?:aday|seçenek))?|mimari\s+seçenekler(?:i)?)\s*:\s*(?P<question>.{10,})$", re.IGNORECASE | re.DOTALL)
PRIORITIES = ("en sade çözüm: az parça, kolay bakım", "dayanıklılık: hata, kesinti ve veri kaybı durumları", "hız ve ölçek: düşük gecikme, büyüyen yük")
AXES = ("gecikme", "bakim", "dayaniklilik", "istege_uyum")
_FAILURE_RE = re.compile(r"hata|kesinti|yeniden dene|geri al|yedek|zaman aşımı|failure|retry|rollback", re.IGNORECASE)


async def _ask(model: str, system: str, user: str) -> dict[str, Any]:
    return wb._extract_json_obj(await wb._ollama_generate(model, system, user, num_predict=900, temperature=0.4)) or {}


def title(candidate: dict[str, Any]) -> str:
    """The candidate's name; a copied placeholder is replaced by how its approach begins."""
    name = str(candidate.get("name", "")).strip().strip("<>")
    if name and "kelimelik" not in name and name.casefold() not in ("kısa ad", "ad", "name", "isim"):
        return name[:60]
    return " ".join(str(candidate.get("approach", "")).split()[:6]).rstrip(".,:")


def rubric(question: str, candidate: dict[str, Any]) -> int:
    """0-10 from facts about the text itself."""
    text = " ".join(str(v) for v in candidate.values()).casefold()
    terms = {w[:5] for w in re.findall(r"\w{5,}", question.casefold())}
    coverage = sum(t in text for t in terms) / len(terms) if terms else 0
    risks = candidate.get("risks")
    return round(coverage * 6) + (2 if _FAILURE_RE.search(text) else 0) + (2 if isinstance(risks, list) and len(risks) >= 2 else 0)


def total(rule: int, critic: dict[str, Any]) -> int:
    marks = [critic.get(a) for a in AXES]
    return rule + sum(min(5, max(1, int(m))) if isinstance(m, int | float) else 1 for m in marks)


async def _run(question: str, count: int) -> AsyncIterator[str]:
    model = await wb.pick_coder_model("qwen3.5:9b")
    scored = []
    for label, priority in zip("ABC", PRIORITIES[:count], strict=False):
        yield f"Aday {label} yazılıyor ({priority.split(':')[0]})...\n"
        candidate = await _ask(model, "Sadece geçerli JSON döndür. Türkçe yaz.",
                               f'Karar: {question}\nÖncelik: {priority}\n{{"name": "<bu yaklaşıma özgü 2-4 kelimelik ad>", "approach": "3-5 cümle", "tradeoffs": "ne kazanılır, ne kaybedilir", "on_failure": "hata olunca ne olur", "risks": ["...", "..."]}}')
        if not candidate.get("approach"):
            continue
        critic = await _ask(model, "Sen tarafsız bir denetçisin. Sadece geçerli JSON döndür.",
                            f"Karar: {question}\nÖneri: {candidate}\nHer eksene 1-5 puan ver (5 en iyi): "
                            '{"gecikme": 0, "bakim": 0, "dayaniklilik": 0, "istege_uyum": 0, "weakness": "en büyük zayıflık"}')
        rule = rubric(question, candidate)
        scored.append((total(rule, critic), rule, label, candidate, critic))
    if not scored:
        yield "Aday üretilemedi."
        return
    rows = "\n".join(f"| {label} | {title(c)} | {' | '.join(str(k.get(a, '-')) for a in AXES)} | {rule} | **{score}** |" for score, rule, label, c, k in scored)
    yield f"\n| aday | ad | gecikme | bakım | dayanıklılık | uyum | kural puanı | toplam |\n|---|---|---|---|---|---|---|---|\n{rows}\n"
    ranked = sorted(scored, key=lambda s: (s[0], s[1]), reverse=True)
    best = ranked[0]
    second_opinion = ""
    if len(ranked) > 1:
        yield "İlk iki aday yargıca (iki sırayla) soruluyor...\n"

        async def ask(system: str, user: str, _schema: dict) -> str:
            return json.dumps(await _ask(model, system + " JSON keys: better (\"1\", \"2\" or \"equal\"), reason.", user))

        winner, reason = await judge.compare(question, str(ranked[0][3]), str(ranked[1][3]), ask)
        label = {"A": ranked[0][2], "B": ranked[1][2]}.get(winner)
        second_opinion = f"\nYargıç (aday {ranked[0][2]} ve {ranked[1][2]}, iki sırayla): " + (f"**{label}** daha iyi — {reason}" if label else f"belirsiz ({reason})") + "\n"
    for _score, _rule, label, c, k in scored:
        yield f"\n**{label} — {title(c)}**: {c.get('approach', '')}\n- Ödünleşim: {c.get('tradeoffs', '')}\n- Hata durumunda: {c.get('on_failure', '')}\n- Zayıf yanı: {k.get('weakness', '-')}\n"
    if second_opinion:
        yield second_opinion
    yield f"\n**Öneri: {best[2]} ({title(best[3])}).** Puanlar bir yardımcıdır; geri dönüşü zor kararda son sözü sen söyle."


def fastpath(prompt: str) -> StreamingResponse | None:
    match = _ASK_RE.match(prompt)
    return chat_stream.reply(_run(match["question"].strip(), int(match["n"] or 3)), "en-iyi-n", "karar") if match else None
