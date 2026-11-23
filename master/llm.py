"""Client for the master agent's own local model, routed through the in-process LLM Gateway (GW-01)."""

import httpx

import config
import gateway


class LLMError(RuntimeError):
    pass


async def chat_structured(system: str, user: str, schema: dict, num_ctx: int) -> str:
    """Ask the master model for a JSON answer that follows ``schema``; returns the raw JSON text."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        res = await gateway.default_client.chat(
            messages,
            model=config.MASTER_MODEL,
            profile="extract",
            format_schema=schema,
            num_predict=config.NUM_PREDICT,
            timeout_s=config.LLM_TIMEOUT_SECONDS,
            feature="requirements_analysis",
            max_retries=0,
        )
    except Exception as exc:
        raise LLMError(f"Master modeline ({config.MASTER_MODEL}) ulaşılamadı: {exc!r}") from exc
    return res.content


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
