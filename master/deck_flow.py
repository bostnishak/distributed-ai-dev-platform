"""Deck generation with a quality loop: generate, score, retry once with the concrete problems, keep the better deck."""

from __future__ import annotations

from typing import Any

import deliverable_score


async def _generate_deck(prompt: str, context_text: str) -> dict[str, Any]:
    import deep_research as dr

    if context_text:
        return await dr.generate_ai_pptx_presentation(prompt, context_text=context_text)
    return await dr.generate_ai_pptx_presentation(prompt)


async def call_generator(prompt: str, context_text: str) -> dict[str, Any]:
    """Quality loop: generate, score, and when the deck is clearly below target retry once with the concrete problems; keep the better deck."""
    best = await _generate_deck(prompt, context_text)
    score, issues = deliverable_score.score_deck(best, prompt)
    if score < deliverable_score.TARGET:
        try:
            again = await _generate_deck(prompt + deliverable_score.feedback(issues), context_text)
        except RuntimeError:
            return best
        if deliverable_score.score_deck(again, prompt)[0] > score:
            return again
    return best
