"""One heavy model on the 8 GB card at a time, and embeddings that never touch it (CPU only).

`exclusive` serialises GPU jobs that need a different model and unloads whatever is resident first, so weights never
spill into slow shared memory. `embed` pins the embedding model to the CPU.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
from collections.abc import AsyncIterator

import httpx

import config

VISION_MODEL = "qwen2.5vl:7b"
EMBED_MODEL = "bge-m3:latest"
_LOCK = asyncio.Lock()


async def loaded_models(client: httpx.AsyncClient) -> list[str]:
    return [m["name"] for m in (await client.get(f"{config.OLLAMA_URL}/api/ps")).json().get("models", [])]


@contextlib.asynccontextmanager
async def exclusive(model: str) -> AsyncIterator[httpx.AsyncClient]:
    async with _LOCK, httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=5.0)) as client:
        for other in await loaded_models(client):
            if other != model:
                await client.post(f"{config.OLLAMA_URL}/api/generate", json={"model": other, "keep_alive": 0})
        try:
            yield client
        finally:
            await client.post(f"{config.OLLAMA_URL}/api/generate", json={"model": model, "keep_alive": 0})


async def look(prompt: str, png: bytes, schema: dict | None = None, model: str = VISION_MODEL) -> str:
    """The vision model's answer about one image; the model is unloaded again afterwards."""
    payload = {"model": model, "stream": False, "options": {"temperature": 0.1, "num_ctx": 6144, "num_predict": 500},
               "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(png).decode()]}]}
    if schema:
        payload["format"] = schema
    async with exclusive(model) as client:
        resp = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return str(resp.json().get("message", {}).get("content", ""))


def embed(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    """Vectors computed on the CPU (num_gpu 0); raises httpx.HTTPError when the model is unavailable."""
    resp = httpx.post(f"{config.OLLAMA_URL}/api/embed", json={"model": model, "input": texts, "options": {"num_gpu": 0}, "keep_alive": "10m"}, timeout=120.0)
    resp.raise_for_status()
    return resp.json()["embeddings"]
