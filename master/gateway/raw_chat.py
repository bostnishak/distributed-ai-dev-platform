"""One non-streaming Ollama chat with an explicit `think` switch (used by the deep-reasoning path; all other calls go through the client)."""

from __future__ import annotations


async def chat(model: str, messages: tuple[str, str], budget: tuple[int, float], think: bool = False) -> str:
    """messages = (system, user); budget = (num_predict, timeout seconds)."""
    import httpx

    import config

    system, user = messages
    payload = {"model": model, "stream": False, "think": think, "keep_alive": "5m", "options": {"num_predict": budget[0], "num_ctx": 10240},
               "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]}
    async with httpx.AsyncClient(timeout=budget[1]) as client:
        resp = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return str((resp.json().get("message") or {}).get("content") or "").strip()
