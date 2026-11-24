"""GW-02: Provider Protocol and Concrete Implementations (Ollama, Distributed Agent, OpenAI-Compat, Optional Cloud).

Cloud providers are strictly disabled unless BOTH `ALLOW_CLOUD_PROVIDERS=true` and the corresponding
API key env var are configured, guaranteeing zero accidental external network calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx

import config
import db

log = logging.getLogger("gateway.providers")


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    node_id: str = "master"


@runtime_checkable
class Provider(Protocol):
    name: str
    is_cloud: bool

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        **opts: Any,
    ) -> ProviderResponse: ...

    def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        *,
        timeout_s: float = 180.0,
    ) -> AsyncIterator[dict[str, Any]]: ...

    async def embed(self, model: str, text: str, timeout_s: float = 30.0) -> list[float]: ...


class OllamaProvider:
    """Primary local provider talking to Ollama HTTP API."""

    name = "ollama"
    is_cloud = False

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or config.OLLAMA_URL).rstrip("/")

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        **opts: Any,
    ) -> ProviderResponse:
        format_schema: dict[str, Any] | None = opts.get("format_schema")
        tools: list[dict[str, Any]] | None = opts.get("tools")
        timeout_s = float(opts.get("timeout_s", 120.0))
        t0 = time.perf_counter()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": options.pop("keep_alive", "10m"),
            "options": options,
        }
        if format_schema is not None:
            payload["format"] = format_schema
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message") or {}
        return ProviderResponse(
            content=str(msg.get("content") or ""),
            model=str(data.get("model") or model),
            provider=self.name,
            tokens_in=int(data.get("prompt_eval_count") or 0),
            tokens_out=int(data.get("eval_count") or 0),
            latency_ms=int((time.perf_counter() - t0) * 1000),
            tool_calls=list(msg.get("tool_calls") or []),
            raw=data,
            node_id="master",
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        *,
        timeout_s: float = 180.0,
    ) -> AsyncIterator[dict[str, Any]]:
        opts = dict(options)
        keep_alive = opts.pop("keep_alive", "10m")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": False,
            "keep_alive": keep_alive,
            "options": opts,
        }
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    piece = (chunk.get("message") or {}).get("content", "")
                    if piece:
                        yield {"type": "token", "content": piece}
                    if chunk.get("done"):
                        yield {
                            "type": "done",
                            "model": str(chunk.get("model") or model),
                            "provider": self.name,
                            "tokens_in": int(chunk.get("prompt_eval_count") or 0),
                            "tokens_out": int(chunk.get("eval_count") or 0),
                        }

    async def embed(self, model: str, text: str, timeout_s: float = 30.0) -> list[float]:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{self.base_url}/api/embed", json={"model": model, "input": text})
            if resp.status_code == 404:
                resp = await client.post(f"{self.base_url}/api/embeddings", json={"model": model, "prompt": text})
            resp.raise_for_status()
            data = resp.json()
            embs = data.get("embeddings") or []
            if embs and isinstance(embs[0], list):
                return [float(x) for x in embs[0]]
            return [float(x) for x in (data.get("embedding") or [])]

    def embed_sync(self, model: str, text: str, timeout_s: float = 1.5) -> list[float]:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(f"{self.base_url}/api/embeddings", json={"model": model, "prompt": text})
            resp.raise_for_status()
            emb = resp.json().get("embedding")
            return [float(x) for x in emb] if isinstance(emb, list) else []

    async def list_tags(self, timeout_s: float = 3.0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return list(resp.json().get("models") or [])

    async def show_model(self, model: str, timeout_s: float = 3.0) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{self.base_url}/api/show", json={"name": model})
            resp.raise_for_status()
            return dict(resp.json())

    async def list_running(self, timeout_s: float = 3.0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(f"{self.base_url}/api/ps")
            resp.raise_for_status()
            return list(resp.json().get("models") or [])


class AgentProvider:
    """GW-02: Dispatches LLM requests onto the distributed agent task queue (`db.py`) and awaits result."""

    name = "agent"
    is_cloud = False

    def __init__(self, target_agent_id: str | None = None, poll_interval_s: float = 0.25) -> None:
        self.target_agent_id = target_agent_id
        self.poll_interval_s = poll_interval_s

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        **opts: Any,
    ) -> ProviderResponse:
        timeout_s = float(opts.get("timeout_s", 60.0))
        t0 = time.perf_counter()
        prompt_blob = "\n\n".join(f"[{m.get('role', 'user')}] {m.get('content', '')}" for m in messages)
        pid = db.create_project("gateway-agent-dispatch", prompt_blob[:1000], None)
        with db.connect() as conn:
            tid = int(
                conn.execute(
                    "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                    "VALUES (?, 'GW1', 1, 'backend', 'Gateway Chat Dispatch', ?, ?, 'planned')",
                    (pid, prompt_blob[:4000], json.dumps({"model": model, "options": options})),
                ).lastrowid
                or 0
            )
        if self.target_agent_id:
            db.assign_task(tid, self.target_agent_id, {"reason": "gateway_agent_provider"})

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            task = db.get_task(tid)
            if task and task.get("status") == "done":
                return ProviderResponse(
                    content=str(task.get("result") or ""),
                    model=model,
                    provider=self.name,
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    node_id=str(task.get("performed_by") or self.target_agent_id or "agent"),
                )
            if task and task.get("status") == "failed":
                raise RuntimeError(f"Agent task {tid} failed: {task.get('result') or ''}")
            await asyncio.sleep(self.poll_interval_s)
        raise TimeoutError(f"Distributed agent task {tid} timed out after {timeout_s}s.")

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        *,
        timeout_s: float = 60.0,
    ) -> AsyncIterator[dict[str, Any]]:
        res = await self.chat(model, messages, options, timeout_s=timeout_s)
        yield {"type": "token", "content": res.content}
        yield {"type": "done", "model": res.model, "provider": self.name, "tokens_in": 0, "tokens_out": 0}

    async def embed(self, model: str, text: str, timeout_s: float = 30.0) -> list[float]:
        raise NotImplementedError("AgentProvider does not serve embeddings directly.")


class OpenAICompatProvider:
    """Local OpenAI-compatible provider (LM Studio, vLLM, llama.cpp server)."""

    name = "openai_compat"
    is_cloud = False

    def __init__(self, base_url: str, api_key: str = "local") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        **opts: Any,
    ) -> ProviderResponse:
        tools: list[dict[str, Any]] | None = opts.get("tools")
        timeout_s = float(opts.get("timeout_s", 120.0))
        t0 = time.perf_counter()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": options.get("temperature", 0.3),
            "max_tokens": options.get("num_predict", 2048),
        }
        if tools:
            payload["tools"] = tools
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{self.base_url}/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        choice = (data.get("choices") or [{}])[0].get("message") or {}
        usage = data.get("usage") or {}
        return ProviderResponse(
            content=str(choice.get("content") or ""),
            model=str(data.get("model") or model),
            provider=self.name,
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
            latency_ms=int((time.perf_counter() - t0) * 1000),
            tool_calls=list(choice.get("tool_calls") or []),
            raw=data,
            node_id="openai_compat",
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        *,
        timeout_s: float = 180.0,
    ) -> AsyncIterator[dict[str, Any]]:
        res = await self.chat(model, messages, options, timeout_s=timeout_s)
        yield {"type": "token", "content": res.content}
        yield {
            "type": "done",
            "model": res.model,
            "provider": self.name,
            "tokens_in": res.tokens_in,
            "tokens_out": res.tokens_out,
        }

    async def embed(self, model: str, text: str, timeout_s: float = 30.0) -> list[float]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(
                f"{self.base_url}/v1/embeddings", headers=headers, json={"model": model, "input": text}
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
            return [float(x) for x in (data[0].get("embedding") or [])] if data else []


def load_optional_cloud_providers() -> dict[str, Provider]:
    """Load optional cloud providers ONLY when ALLOW_CLOUD_PROVIDERS=true AND key is configured."""
    allow_cloud = os.environ.get("ALLOW_CLOUD_PROVIDERS", "false").strip().lower() in ("1", "true", "yes")
    if not allow_cloud:
        log.info("Bulut saglayicilar kapali (ALLOW_CLOUD_PROVIDERS=false).")
        return {}
    loaded: dict[str, Provider] = {}
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        p = OpenAICompatProvider("https://api.openai.com", api_key=openai_key)
        p.name = "openai_cloud"
        p.is_cloud = True
        loaded["openai_cloud"] = p
    else:
        log.info("OpenAI bulut saglayici kapali (anahtar yok).")
    return loaded
