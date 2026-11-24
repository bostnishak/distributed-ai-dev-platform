"""EPK-23: OpenAI-Compatible REST API (/v1/models, /v1/chat/completions, /v1/embeddings)."""

from __future__ import annotations

import hashlib
import math
import secrets
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

import config

router = APIRouter(prefix="/v1", tags=["openai-compat"])


def _deterministic_embedding(text: str, dims: int = 64) -> list[float]:
    raw: list[float] = []
    for i in range(dims):
        digest = hashlib.sha256(f"{text}:{i}".encode()).digest()
        val = (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) * 2.0 - 1.0
        raw.append(val)
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [round(v / norm, 6) for v in raw]


class OpenAIChatRequest(BaseModel):
    model: str = Field(default="dadp-local", max_length=80)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=32768)
    stream: bool = False


class OpenAIEmbeddingsRequest(BaseModel):
    model: str = Field(default="dadp-embed-local", max_length=80)
    input: str | list[str]


@router.get("/models")
async def openai_list_models():
    """OpenAI-compatible model catalog listing local DADP models."""
    now = int(time.time())
    models = sorted({config.MASTER_MODEL, config.STUDIO_CODER_MODEL, "dadp-local", "dadp-embed-local"})
    return {
        "object": "list",
        "data": [{"id": m, "object": "model", "created": now, "owned_by": "dadp-local"} for m in models],
    }


@router.post("/chat/completions")
async def openai_chat_completions(body: OpenAIChatRequest):
    """OpenAI-compatible /v1/chat/completions endpoint backed by DADP deterministic calculator & local summary."""
    from assistant import try_calculate

    last_user = next((str(m.get("content") or "") for m in reversed(body.messages) if m.get("role") == "user"), "")
    calc = try_calculate(last_user) if last_user else None
    reply = calc if calc is not None else f"[DADP Yerel Model: {body.model}] İstek alındı: {last_user[:300]}"
    p_tok = max(1, len(last_user) // 4)
    c_tok = max(1, len(reply) // 4)
    return {
        "id": f"chatcmpl-{secrets.token_hex(8)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": p_tok, "completion_tokens": c_tok, "total_tokens": p_tok + c_tok},
    }


@router.post("/embeddings")
async def openai_embeddings(body: OpenAIEmbeddingsRequest):
    """OpenAI-compatible /v1/embeddings endpoint returning unit-normalized local vectors."""
    inputs = [body.input] if isinstance(body.input, str) else list(body.input)
    data = [
        {"object": "embedding", "index": i, "embedding": _deterministic_embedding(str(txt), dims=64)}
        for i, txt in enumerate(inputs[:64])
    ]
    tok_count = sum(max(1, len(str(t)) // 4) for t in inputs[:64])
    return {
        "object": "list",
        "model": body.model,
        "data": data,
        "usage": {"prompt_tokens": tok_count, "total_tokens": tok_count},
    }
