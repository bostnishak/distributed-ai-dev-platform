"""OPS-10: Deterministic VCR-Style Ollama-Compatible Fake Server for E2E, Orchestrator & Chaos Tests."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse


def create_fake_ollama_app(
    *,
    canned_responses: dict[str, str] | None = None,
    models: list[str] | None = None,
    inject_error: str | None = None,
) -> FastAPI:
    """Create an in-process Ollama-compatible FastAPI ASGI test double (supports streaming, tools, embed, faults)."""
    app = FastAPI(title="Fake Ollama VCR Server (OPS-10)")
    state: dict[str, Any] = {
        "canned": dict(canned_responses or {}),
        "models": list(models or ["qwen3.5:9b", "qwen2.5-coder:7b", "bge-m3:latest"]),
        "inject_error": inject_error,
        "requests": [],
    }

    @app.get("/api/tags")
    async def tags():
        if state["inject_error"] == "500":
            raise HTTPException(status_code=500, detail="Injected fault")
        return {"models": [{"name": m, "size": 4_000_000_000} for m in state["models"]]}

    @app.get("/api/ps")
    async def ps():
        return {"models": [{"name": state["models"][0]}]} if state["models"] else {"models": []}

    @app.post("/api/show")
    async def show(body: dict[str, Any]):
        return {"model_info": {"general.context_length": 32768}, "capabilities": ["completion", "tools"]}

    @app.post("/api/chat")
    async def chat(body: dict[str, Any]):
        state["requests"].append(body)
        if state["inject_error"]:
            raise HTTPException(status_code=503, detail=f"Injected Ollama fault: {state['inject_error']}")
        msgs = body.get("messages") or []
        last_user = str(msgs[-1].get("content") or "") if msgs else ""
        reply = "Sahte Ollama yanıtı."
        for key, val in state["canned"].items():
            if key.lower() in last_user.lower():
                reply = val
                break
        model = str(body.get("model") or state["models"][0])
        if body.get("stream"):
            async def _gen():
                for word in reply.split(" "):
                    yield json.dumps({"model": model, "message": {"role": "assistant", "content": word + " "}, "done": False}) + "\n"
                yield json.dumps({"model": model, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 20, "eval_count": len(reply.split())}) + "\n"

            return StreamingResponse(_gen(), media_type="application/x-ndjson")
        return {
            "model": model,
            "message": {"role": "assistant", "content": reply},
            "done": True,
            "prompt_eval_count": 20,
            "eval_count": len(reply.split()),
        }

    @app.post("/api/embed")
    async def embed(body: dict[str, Any]):
        return {"embeddings": [[0.25, 0.25, 0.25, 0.25] * 16]}

    app.state.fake_state = state
    return app
