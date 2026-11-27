"""The critic comes from a different model family than the writer.

A 7B model asked to review its own work tends to agree with its own mistakes. For judgements no program can make, an
installed model of another family is asked; the gateway's priority gate keeps only one of them on the card at a time.
"""

from __future__ import annotations

import logging
import os

import httpx

import config

PREFERRED = ("deepseek-r1:8b", "llama3.2:3b", "phi4-mini:latest")  # fit an 8 GB card; first installed one of another family
_FAMILIES = ("qwen", "deepseek", "llama", "gemma", "phi", "mistral")
_NOT_CRITICS = ("embed", "bge", "vl", "ballooner")
_log = logging.getLogger(__name__)


def family(model: str) -> str:
    low = model.lower()
    return next((name for name in _FAMILIES if name in low), low.split(":")[0])


def pick(writer: str, installed: list[str]) -> str:
    """The writer itself when no model of another family is installed."""
    wanted = os.environ.get("CRITIC_MODEL", "")
    usable = [m for m in installed if family(m) != family(writer) and not any(word in m.lower() for word in _NOT_CRITICS)]
    return next((m for m in (wanted, *PREFERRED) if m in usable), usable[0] if usable else writer)


async def critic_for(writer: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            reply = await client.get(f"{config.OLLAMA_URL}/api/tags")
            reply.raise_for_status()
            return pick(writer, [m.get("name", "") for m in reply.json().get("models", [])])
    except (httpx.HTTPError, OSError, ValueError, AttributeError) as exc:
        _log.warning("kurulu modeller okunamadı, eleştiri yazan modelde kalıyor: %s", exc)
        return writer
