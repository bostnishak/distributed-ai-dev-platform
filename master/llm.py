"""Client for the master agent's own local model, using Ollama's native API.

The native /api/chat endpoint is used instead of the LiteLLM gateway because it reliably
supports what requirements analysis needs: a JSON schema in ``format`` (structured output),
``options.num_ctx`` for long documents and ``think: false`` to skip the slow thinking phase.
"""

import httpx

import config


class LLMError(RuntimeError):
    pass


async def chat_structured(system: str, user: str, schema: dict, num_ctx: int) -> str:
    """Ask the master model for a JSON answer that follows ``schema``; returns the raw JSON text."""
    payload = {
        "model": config.MASTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": schema,
        "stream": False,
        "think": False,
        "options": {"num_ctx": num_ctx, "num_predict": config.NUM_PREDICT, "temperature": 0},
    }
    try:
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
    except httpx.HTTPError as exc:
        raise LLMError(f"Master modeline ({config.MASTER_MODEL}) ulaşılamadı: {exc!r}") from exc
    if resp.status_code != 200:
        raise LLMError(f"Ollama hata döndürdü ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    if data.get("done_reason") == "length":
        raise LLMError("Model yanıtı üretim sınırında kesildi (NUM_PREDICT).")
    return data["message"]["content"]


async def status() -> dict:
    """Whether the master's Ollama is reachable and has the configured model."""
    result = {"model": config.MASTER_MODEL, "reachable": False, "model_available": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
        resp.raise_for_status()
    except httpx.HTTPError:
        return result
    result["reachable"] = True
    names = {m.get("name") for m in resp.json().get("models", [])}
    # Ollama lists untagged models with an explicit ":latest" suffix.
    result["model_available"] = bool({config.MASTER_MODEL, f"{config.MASTER_MODEL}:latest"} & names)
    return result
