"""GW-01, GW-07..GW-15, GW-18..GW-20: Unified In-Process LLM Gateway Client & Status API."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

import config
from gateway import prompts as gw_prompts
from gateway import registry as gw_registry
from gateway.providers import (
    OllamaProvider,
    Provider,
    ProviderResponse,
    load_optional_cloud_providers,
)
from log_sanitizer import redact_sensitive_text

log = logging.getLogger("gateway.client")
router = APIRouter(prefix="/api/gateway", tags=["gateway"])

TModel = TypeVar("TModel", bound=BaseModel)


# ---------------------------------------------------------------- GW-07 Decoding Profiles

DECODING_PROFILES: dict[str, dict[str, Any]] = {
    "factual": {"temperature": 0.1, "top_p": 0.8, "repeat_penalty": 1.08},
    "code": {"temperature": 0.2, "top_p": 0.85, "repeat_penalty": 1.06},
    "extract": {"temperature": 0.0, "top_p": 0.8, "repeat_penalty": 1.02},
    "creative": {"temperature": 0.8, "top_p": 0.92, "repeat_penalty": 1.05},
    "analytic": {"temperature": 0.3, "top_p": 0.85, "repeat_penalty": 1.08},
}

TASK_TO_PROFILE: dict[str, str] = {
    "factual": "factual",
    "research": "factual",
    "analiz": "analytic",
    "kod": "code",
    "code": "code",
    "extract": "extract",
    "creative": "creative",
    "genel": "analytic",
    "short": "factual",
    "lesson": "analytic",
}


# ---------------------------------------------------------------- GW-08 Classified Errors & Circuit Breaker

class GatewayError(RuntimeError):
    code = "gateway_error"


class ConnectionFailedError(GatewayError):
    code = "connection_failed"


class TimeoutFailureError(GatewayError):
    code = "timeout"


class ModelNotFoundError(GatewayError):
    code = "model_not_found"


class OOMError(GatewayError):
    code = "oom"


class ContextOverflowError(GatewayError):
    code = "context_overflow"


class BudgetExceededError(GatewayError):
    code = "budget_exceeded"


def classify_error(exc: Exception) -> GatewayError:
    if isinstance(exc, GatewayError):
        return exc
    msg = str(exc).lower()
    if isinstance(exc, (httpx.ConnectError, ConnectionRefusedError)) or "connection refused" in msg:
        return ConnectionFailedError(
            "Ollama'ya ulaşılamıyor. Şu adımları dene: 1) `ollama serve` çalıştır, "
            "2) `http://127.0.0.1:11434/api/tags` yanıtını kontrol et, 3) güvenlik duvarını doğrula."
        )
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)) or "timed out" in msg:
        return TimeoutFailureError(f"Model isteği zaman aşımına uğradı: {exc}")
    if "not found" in msg or "404" in msg:
        return ModelNotFoundError(f"İstenen model yüklü değil: {exc}")
    if "out of memory" in msg or "oom" in msg or "vram" in msg:
        return OOMError(f"Bellek/VRAM yetersiz: {exc}")
    if "context length" in msg or "too long" in msg:
        return ContextOverflowError(f"Bağlam penceresi aşıldı: {exc}")
    return GatewayError(str(exc))


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def is_open(self, key: str) -> bool:
        opened = self._opened_at.get(key)
        if opened is None:
            return False
        if time.monotonic() - opened >= self.recovery_seconds:
            self._opened_at.pop(key, None)
            self._failures[key] = 0
            return False
        return True

    def record_success(self, key: str) -> None:
        self._failures[key] = 0
        self._opened_at.pop(key, None)

    def record_failure(self, key: str) -> None:
        n = self._failures.get(key, 0) + 1
        self._failures[key] = n
        if n >= self.failure_threshold:
            self._opened_at[key] = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        return {k: {"open": self.is_open(k), "failures": v} for k, v in self._failures.items()}


# ---------------------------------------------------------------- GW-09 Cancellation & Priority Queue

@dataclass
class CancellationToken:
    cancelled: bool = False
    reason: str = ""

    def cancel(self, reason: str = "Kullanıcı tarafından iptal edildi") -> None:
        self.cancelled = True
        self.reason = reason

    def check(self) -> None:
        if self.cancelled:
            raise asyncio.CancelledError(self.reason or "İstek iptal edildi.")


# ---------------------------------------------------------------- GW-13, GW-14, GW-15 SQLite Store

def _gw_db_path() -> Path:
    p = Path(config.DATA_DIR) / "gateway.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _gw_conn() -> sqlite3.Connection:
    import dbconn

    return dbconn.open_db(_gw_db_path())


def init_gateway_db() -> None:
    gw_registry.init_registry_db()
    with _gw_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                profile TEXT NOT NULL,
                value_json TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS llm_calls (
                trace_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'default',
                feature TEXT NOT NULL DEFAULT 'chat',
                template_version TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                profile TEXT NOT NULL,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                error TEXT NOT NULL DEFAULT '',
                prompt_summary TEXT NOT NULL DEFAULT '',
                response_summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_llm_calls_run ON llm_calls(run_id);
            CREATE INDEX IF NOT EXISTS idx_llm_calls_user ON llm_calls(user_id, created_at);
            """
        )


def _record_call(
    *,
    run_id: str,
    user_id: str,
    feature: str,
    template_version: str,
    provider: str,
    model: str,
    profile: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    status: str,
    error: str = "",
    prompt_summary: str = "",
    response_summary: str = "",
) -> str:
    init_gateway_db()
    tid = f"trc-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    with _gw_conn() as conn:
        conn.execute(
            """
            INSERT INTO llm_calls
                (trace_id, run_id, user_id, feature, template_version, provider, model, profile,
                 tokens_in, tokens_out, latency_ms, status, error, prompt_summary, response_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tid,
                run_id or tid,
                user_id,
                feature,
                template_version,
                provider,
                model,
                profile,
                int(tokens_in),
                int(tokens_out),
                int(latency_ms),
                status,
                redact_sensitive_text(error)[:300],
                redact_sensitive_text(prompt_summary)[:160],
                redact_sensitive_text(response_summary)[:160],
                now,
            ),
        )
    return tid


def get_run_traces(run_id: str) -> list[dict[str, Any]]:
    init_gateway_db()
    with _gw_conn() as conn:
        rows = conn.execute("SELECT * FROM llm_calls WHERE run_id = ? ORDER BY created_at ASC", (run_id,)).fetchall()
    return [dict(r) for r in rows]


def _daily_user_tokens(user_id: str) -> int:
    init_gateway_db()
    today_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
    with _gw_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) AS tot FROM llm_calls WHERE user_id = ? AND created_at LIKE ?",
            (user_id, f"{today_prefix}%"),
        ).fetchone()
    return int(row["tot"] or 0) if row else 0


# ---------------------------------------------------------------- Unified LLMClient

@dataclass
class ChatResult:
    content: str
    model: str
    provider: str
    node_id: str
    profile: str
    trace_id: str
    run_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cached: bool = False
    fallback_note: str = ""
    selection_reason: str = ""
    context_info: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class LLMClient:
    """GW-01: Single in-process LLM client with providers, caching, budgets, retries, and tracing."""

    def __init__(self, providers: dict[str, Provider] | None = None) -> None:
        self.providers: dict[str, Provider] = {}
        if providers is not None:
            self.providers.update(providers)
        else:
            self.providers["ollama"] = OllamaProvider()
            self.providers.update(load_optional_cloud_providers())
        self.breaker = CircuitBreaker()
        self._cache_hits = 0
        self._cache_misses = 0
        self._active_requests = 0
        self._sem = asyncio.Semaphore(4)
        self.daily_token_budget: int = 0  # 0 = unlimited unless configured
        init_gateway_db()

    def register_provider(self, provider: Provider) -> None:
        self.providers[provider.name] = provider

    def _get_provider(self, name: str) -> Provider:
        if name not in self.providers:
            raise GatewayError(f"Sağlayıcı yüklü değil veya kapalı: {name}")
        return self.providers[name]

    def _check_budget(self, user_id: str) -> None:
        if self.daily_token_budget > 0:
            used = _daily_user_tokens(user_id)
            if used >= self.daily_token_budget:
                raise BudgetExceededError(
                    f"Günlük token bütçesi aşıldı ({used}/{self.daily_token_budget})."
                )

    def _cache_key(self, model: str, profile: str, payload: Any) -> str:
        raw = json.dumps({"m": model, "p": profile, "x": payload}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> Any | None:
        with _gw_conn() as conn:
            row = conn.execute("SELECT value_json, expires_at FROM llm_cache WHERE cache_key = ?", (key,)).fetchone()
        if not row or float(row["expires_at"]) < time.time():
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return json.loads(row["value_json"])

    def _cache_put(self, key: str, model: str, profile: str, value: Any, ttl_s: float = 3600.0) -> None:
        with _gw_conn() as conn:
            conn.execute(
                """
                INSERT INTO llm_cache (cache_key, model, profile, value_json, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    expires_at = excluded.expires_at
                """,
                (key, model, profile, json.dumps(value, ensure_ascii=False), time.time() + ttl_s, datetime.now(UTC).isoformat()),
            )

    def _build_options(
        self,
        profile: str,
        num_ctx: int,
        num_predict: int | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        base = dict(DECODING_PROFILES.get(profile, DECODING_PROFILES["analytic"]))
        base["num_ctx"] = num_ctx
        base["num_predict"] = int(num_predict or config.ASSISTANT_NUM_PREDICT)
        if seed is not None:
            base["seed"] = int(seed)
        return base

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        provider_name: str | None = None,
        task_type: str = "genel",
        profile: str | None = None,
        fallback_models: list[str] | None = None,
        user_id: str = "default",
        run_id: str | None = None,
        feature: str = "chat",
        template_version: str = "",
        use_cache: bool = False,
        private_user_data: bool = True,
        format_schema: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        seed: int | None = None,
        num_predict: int | None = None,
        max_retries: int = 2,
        cancel_token: CancellationToken | None = None,
        timeout_s: float = 120.0,
    ) -> ChatResult:
        self._check_budget(user_id)
        if cancel_token:
            cancel_token.check()

        rid = run_id or f"run-{uuid.uuid4().hex[:10]}"
        prof = profile or TASK_TO_PROFILE.get(task_type, "analytic")
        est_in = gw_registry.estimate_tokens(messages)
        sel = gw_registry.select_model(task_type=task_type, required_ctx=est_in + 512, fallback_model=model)
        chosen_model = model or sel.model
        chosen_prov = provider_name or sel.provider
        if chosen_prov not in self.providers:
            chosen_prov = next(iter(self.providers))

        fitted_msgs, ctx_info = gw_registry.fit_messages_to_context(messages, sel.ctx_max)
        num_ctx = gw_registry.choose_dynamic_num_ctx(ctx_info["ctx_used"], sel.ctx_max)
        opts = self._build_options(prof, num_ctx, num_predict=num_predict, seed=seed)

        # GW-13: Content-addressed cache (STRICTLY skipped when private_user_data=True)
        cache_k = ""
        if use_cache and not private_user_data and not tools:
            cache_k = self._cache_key(chosen_model, prof, {"msgs": fitted_msgs, "schema": format_schema})
            hit = self._cache_get(cache_k)
            if hit is not None:
                tid = _record_call(
                    run_id=rid,
                    user_id=user_id,
                    feature=feature,
                    template_version=template_version,
                    provider=chosen_prov,
                    model=chosen_model,
                    profile=prof,
                    tokens_in=0,
                    tokens_out=0,
                    latency_ms=0,
                    status="cached",
                    prompt_summary=str(fitted_msgs[-1].get("content") or ""),
                    response_summary=str(hit.get("content") or ""),
                )
                return ChatResult(
                    content=str(hit.get("content") or ""),
                    model=chosen_model,
                    provider=chosen_prov,
                    node_id="cache",
                    profile=prof,
                    trace_id=tid,
                    run_id=rid,
                    cached=True,
                    selection_reason=sel.reason,
                    context_info=ctx_info,
                )

        candidates = [chosen_model, *(fallback_models or [])]
        last_err: GatewayError | None = None
        fallback_note = ""

        async with self._sem:
            self._active_requests += 1
            try:
                for cand_idx, cand_model in enumerate(candidates):
                    cb_key = f"{chosen_prov}:{cand_model}"
                    if self.breaker.is_open(cb_key):
                        continue
                    prov = self._get_provider(chosen_prov)
                    for attempt in range(max_retries + 1):
                        if cancel_token:
                            cancel_token.check()
                        try:
                            res: ProviderResponse = await prov.chat(
                                cand_model,
                                fitted_msgs,
                                dict(opts),
                                format_schema=format_schema,
                                tools=tools,
                                timeout_s=timeout_s,
                            )
                            self.breaker.record_success(cb_key)
                            if cand_idx > 0:
                                fallback_note = f"{chosen_model} yüklenemedi, {cand_model} kullanıldı."
                            if cache_k:
                                self._cache_put(cache_k, cand_model, prof, {"content": res.content})
                            tid = _record_call(
                                run_id=rid,
                                user_id=user_id,
                                feature=feature,
                                template_version=template_version,
                                provider=res.provider,
                                model=res.model,
                                profile=prof,
                                tokens_in=res.tokens_in or est_in,
                                tokens_out=res.tokens_out or gw_registry.estimate_tokens(res.content),
                                latency_ms=res.latency_ms,
                                status="ok",
                                prompt_summary=str(fitted_msgs[-1].get("content") or ""),
                                response_summary=res.content,
                            )
                            return ChatResult(
                                content=res.content,
                                model=res.model,
                                provider=res.provider,
                                node_id=res.node_id,
                                profile=prof,
                                trace_id=tid,
                                run_id=rid,
                                tokens_in=res.tokens_in or est_in,
                                tokens_out=res.tokens_out or gw_registry.estimate_tokens(res.content),
                                latency_ms=res.latency_ms,
                                fallback_note=fallback_note,
                                selection_reason=sel.reason,
                                context_info=ctx_info,
                                tool_calls=res.tool_calls,
                            )
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            last_err = classify_error(exc)
                            self.breaker.record_failure(cb_key)
                            if isinstance(last_err, (ModelNotFoundError, OOMError)):
                                break  # immediately advance to fallback model
                            if attempt < max_retries:
                                await asyncio.sleep(0.15 * (2**attempt))
            finally:
                self._active_requests = max(0, self._active_requests - 1)

        err = last_err or GatewayError("Tüm aday modeller başarısız oldu.")
        _record_call(
            run_id=rid,
            user_id=user_id,
            feature=feature,
            template_version=template_version,
            provider=chosen_prov,
            model=chosen_model,
            profile=prof,
            tokens_in=0,
            tokens_out=0,
            latency_ms=0,
            status="error",
            error=str(err),
            prompt_summary=str(fitted_msgs[-1].get("content") or ""),
        )
        raise err

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        provider_name: str | None = None,
        task_type: str = "genel",
        profile: str | None = None,
        user_id: str = "default",
        run_id: str | None = None,
        cancel_token: CancellationToken | None = None,
        timeout_s: float = 180.0,
    ) -> AsyncIterator[dict[str, Any]]:
        self._check_budget(user_id)
        rid = run_id or f"run-{uuid.uuid4().hex[:10]}"
        prof = profile or TASK_TO_PROFILE.get(task_type, "analytic")
        est_in = gw_registry.estimate_tokens(messages)
        sel = gw_registry.select_model(task_type=task_type, required_ctx=est_in + 512, fallback_model=model)
        chosen_model = model or sel.model
        chosen_prov = provider_name or sel.provider
        if chosen_prov not in self.providers:
            chosen_prov = next(iter(self.providers))
        fitted_msgs, ctx_info = gw_registry.fit_messages_to_context(messages, sel.ctx_max)
        num_ctx = gw_registry.choose_dynamic_num_ctx(ctx_info["ctx_used"], sel.ctx_max)
        opts = self._build_options(prof, num_ctx)
        prov = self._get_provider(chosen_prov)

        t0 = time.perf_counter()
        acc: list[str] = []
        tok_in, tok_out = est_in, 0
        try:
            async for evt in prov.stream(chosen_model, fitted_msgs, opts, timeout_s=timeout_s):
                if cancel_token and cancel_token.cancelled:
                    break
                if evt.get("type") == "token":
                    acc.append(str(evt.get("content") or ""))
                elif evt.get("type") == "done":
                    tok_in = int(evt.get("tokens_in") or est_in)
                    tok_out = int(evt.get("tokens_out") or gw_registry.estimate_tokens("".join(acc)))
                    evt["ctx_info"] = ctx_info
                    evt["selection_reason"] = sel.reason
                    evt["run_id"] = rid
                yield evt
            _record_call(
                run_id=rid,
                user_id=user_id,
                feature="stream",
                template_version="",
                provider=chosen_prov,
                model=chosen_model,
                profile=prof,
                tokens_in=tok_in,
                tokens_out=tok_out,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                status="cancelled" if (cancel_token and cancel_token.cancelled) else "ok",
                prompt_summary=str(fitted_msgs[-1].get("content") or ""),
                response_summary="".join(acc),
            )
        except Exception as exc:
            err = classify_error(exc)
            _record_call(
                run_id=rid,
                user_id=user_id,
                feature="stream",
                template_version="",
                provider=chosen_prov,
                model=chosen_model,
                profile=prof,
                tokens_in=0,
                tokens_out=0,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                status="error",
                error=str(err),
            )
            raise err from exc

    async def embed(
        self,
        text: str,
        *,
        model: str = "bge-m3:latest",
        provider_name: str = "ollama",
        use_cache: bool = True,
        private_user_data: bool = False,
    ) -> list[float]:
        """GW-01 & GW-13: Deterministic embedding call with content-addressed cache."""
        cache_k = ""
        if use_cache and not private_user_data:
            cache_k = self._cache_key(model, "embed", text)
            hit = self._cache_get(cache_k)
            if isinstance(hit, list):
                return [float(x) for x in hit]
        prov = self._get_provider(provider_name)
        vec = await prov.embed(model, text)
        if cache_k and vec:
            self._cache_put(cache_k, model, "embed", vec, ttl_s=86400.0)
        return vec

    async def structured(
        self,
        messages: list[dict[str, Any]],
        schema_cls: type[TModel],
        *,
        model: str | None = None,
        provider_name: str | None = None,
        max_repairs: int = 2,
        user_id: str = "default",
        run_id: str | None = None,
    ) -> TModel:
        """GW-11: Schema-constrained JSON generation with Pydantic validation and up to 2 repair retries."""
        schema_dict = schema_cls.model_json_schema()
        work_msgs = list(messages)
        last_err: Exception | None = None

        for attempt in range(max_repairs + 1):
            res = await self.chat(
                work_msgs,
                model=model,
                provider_name=provider_name,
                task_type="extract",
                profile="extract",
                format_schema=schema_dict,
                user_id=user_id,
                run_id=run_id,
                feature="structured",
            )
            raw = res.content.strip()
            candidate_json = raw
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                candidate_json = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            try:
                parsed = json.loads(candidate_json)
                return schema_cls.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_err = exc
                if attempt < max_repairs:
                    work_msgs.append({"role": "assistant", "content": raw[:1200]})
                    work_msgs.append({
                        "role": "user",
                        "content": (
                            f"JSON doğrulama hatası: {exc}\n"
                            f"Lütfen SADECE şu JSON şemasına tam uyan geçerli JSON döndür: {json.dumps(schema_dict)}"
                        ),
                    })
        raise GatewayError(f"Yapılandırılmış çıktı {max_repairs} onarım denemesinde doğrulanamadı: {last_err}")

    async def call_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        model: str | None = None,
        provider_name: str | None = None,
        native_tools_supported: bool = True,
        user_id: str = "default",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """GW-12: Unified tool calling — native Ollama `tools` OR schema-constrained ReAct JSON fallback."""
        if native_tools_supported:
            res = await self.chat(
                messages,
                model=model,
                provider_name=provider_name,
                task_type="kod",
                profile="extract",
                tools=tools,
                user_id=user_id,
                run_id=run_id,
                feature="tool_call",
            )
            if res.tool_calls:
                tc = res.tool_calls[0]
                fn = tc.get("function") or tc
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    args = json.loads(args)
                return {"type": "tool_call", "name": str(fn.get("name") or ""), "arguments": args, "model": res.model}
            return {"type": "final", "content": res.content, "model": res.model}

        # Fallback for models without native `tools` capability: schema-constrained ReAct JSON
        class ReActDecision(BaseModel):
            action: str
            arguments: dict[str, Any] = {}
            final_answer: str = ""

        tool_desc = json.dumps([{"name": t["function"]["name"], "desc": t["function"].get("description", "")} for t in tools], ensure_ascii=False)
        react_msgs = [
            *messages,
            {"role": "system", "content": f"Kullanılabilir araçlar: {tool_desc}. Araç çağıracaksan action alanına araç adını, bitiriyorsan action='final' yaz."},
        ]
        dec = await self.structured(react_msgs, ReActDecision, model=model, provider_name=provider_name, user_id=user_id, run_id=run_id)
        if dec.action != "final":
            return {"type": "tool_call", "name": dec.action, "arguments": dec.arguments, "model": model or ""}
        return {"type": "final", "content": dec.final_answer, "model": model or ""}

    async def run_council(
        self,
        prompt: str,
        *,
        proposer_models: list[str],
        critic_model: str,
        judge_model: str,
        provider_name: str | None = None,
        user_id: str = "default",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """GW-18: Multi-model independent proposer -> critic -> judge synthesis with disagreement tracking."""
        rid = run_id or f"council-{uuid.uuid4().hex[:8]}"
        proposals: list[dict[str, str]] = []
        for pm in proposer_models[:3]:
            r = await self.chat(
                [{"role": "user", "content": prompt}],
                model=pm,
                provider_name=provider_name,
                task_type="analiz",
                profile="analytic",
                user_id=user_id,
                run_id=rid,
                feature="council_proposer",
            )
            proposals.append({"model": r.model, "answer": r.content})

        joined = "\n\n".join(f"[{p['model']}]:\n{p['answer']}" for p in proposals)
        critic = await self.chat(
            [{"role": "user", "content": f"Soru: {prompt}\n\nÖneriler:\n{joined}\n\nÇelişkileri, hataları ve eksik kanıtları listele."}],
            model=critic_model,
            provider_name=provider_name,
            task_type="analiz",
            profile="factual",
            user_id=user_id,
            run_id=rid,
            feature="council_critic",
        )
        judge = await self.chat(
            [{"role": "user", "content": f"Soru: {prompt}\n\nÖneriler:\n{joined}\n\nEleştirmen Notları:\n{critic.content}\n\nEn doğru nihai sentezi yaz."}],
            model=judge_model,
            provider_name=provider_name,
            task_type="analiz",
            profile="factual",
            user_id=user_id,
            run_id=rid,
            feature="council_judge",
        )
        return {
            "run_id": rid,
            "proposals": proposals,
            "critique": critic.content,
            "final_answer": judge.content,
            "judge_model": judge.model,
        }

    async def cascade_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        fast_model: str,
        strong_model: str,
        confidence_threshold: float = 0.72,
        provider_name: str | None = None,
        user_id: str = "default",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """GW-19: FrugalGPT-style cascade: try fast small model first; escalate only if confidence < threshold."""
        first = await self.chat(
            messages,
            model=fast_model,
            provider_name=provider_name,
            task_type="short",
            profile="factual",
            user_id=user_id,
            run_id=run_id,
            feature="cascade_fast",
        )
        # Heuristic confidence signal (uncertainty phrases or overly brief empty answers trigger escalation)
        low = first.content.lower()
        uncertain = any(k in low for k in ("emin değilim", "bilmiyorum", "tahmin", "belirsiz", "not sure")) or len(first.content.strip()) < 12
        conf = 0.45 if uncertain else 0.88
        if conf >= confidence_threshold:
            return {"escalated": False, "confidence": conf, "result": first}

        strong = await self.chat(
            messages,
            model=strong_model,
            provider_name=provider_name,
            task_type="analiz",
            profile="factual",
            user_id=user_id,
            run_id=run_id,
            feature="cascade_escalated",
        )
        return {"escalated": True, "confidence": conf, "result": strong, "initial_model": fast_model}

    async def gateway_status(self) -> dict[str, Any]:
        """GW-20: Live gateway health, warm models, queue depth, circuit breakers, and 5-min error rate."""
        ollama_ok = False
        reason = ""
        warm_models: list[str] = []
        if "ollama" in self.providers and isinstance(self.providers["ollama"], OllamaProvider):
            try:
                running = await self.providers["ollama"].list_running()
                warm_models = [str(m.get("name") or "") for m in running]
                ollama_ok = True
            except Exception as exc:
                reason = f"Ollama erişilemiyor: {exc}"

        cutoff = datetime.fromtimestamp(time.time() - 300, tz=UTC).isoformat()
        with _gw_conn() as conn:
            tot = conn.execute("SELECT COUNT(*) AS c FROM llm_calls WHERE created_at >= ?", (cutoff,)).fetchone()["c"]
            errs = conn.execute("SELECT COUNT(*) AS c FROM llm_calls WHERE created_at >= ? AND status='error'", (cutoff,)).fetchone()["c"]

        return {
            "status": "healthy" if ollama_ok else "degraded",
            "reason": reason or "Tüm yerel sağlayıcılar hazır",
            "providers": sorted(self.providers.keys()),
            "warm_models": warm_models,
            "registered_models": len(gw_registry.list_models()),
            "active_queue_depth": self._active_requests,
            "error_rate_5m": round((errs / tot), 3) if tot else 0.0,
            "circuit_breakers": self.breaker.snapshot(),
            "cache": {"hits": self._cache_hits, "misses": self._cache_misses},
        }


# Singleton gateway instance
default_client = LLMClient()


@router.get("/status")
async def api_gateway_status():
    return await default_client.gateway_status()


_MODELS_CACHE: dict[str, Any] = {"ts": 0.0, "models": None}
_MODELS_CACHE_TTL = 30.0


@router.get("/models")
async def api_gateway_models():
    """Return registered LLM models with a 30s TTL cache so UI opens under 100 ms (ALT-10)."""
    now = time.monotonic()
    cached = _MODELS_CACHE.get("models")
    if cached is not None and (now - float(_MODELS_CACHE.get("ts") or 0.0)) < _MODELS_CACHE_TTL:
        return {"models": cached, "cached": True}
    if "ollama" in default_client.providers and isinstance(default_client.providers["ollama"], OllamaProvider):
        try:
            await gw_registry.sync_from_ollama(default_client.providers["ollama"])
        except Exception as exc:
            logging.getLogger(__name__).debug("Ollama model sync skipped: %s", exc)
    models = gw_registry.list_models()
    _MODELS_CACHE["ts"] = now
    _MODELS_CACHE["models"] = models
    return {"models": models, "cached": False}


@router.get("/traces/{run_id}")
async def api_gateway_traces(run_id: str):
    traces = get_run_traces(run_id)
    if not traces:
        raise HTTPException(status_code=404, detail="Bu run_id için çağrı izi bulunamadı.")
    return {"run_id": run_id, "calls": traces}


__all__ = [
    "DECODING_PROFILES",
    "TASK_TO_PROFILE",
    "BudgetExceededError",
    "CancellationToken",
    "ChatResult",
    "CircuitBreaker",
    "ConnectionFailedError",
    "ContextOverflowError",
    "GatewayError",
    "LLMClient",
    "ModelNotFoundError",
    "OOMError",
    "TimeoutFailureError",
    "classify_error",
    "default_client",
    "get_run_traces",
    "gw_prompts",
    "gw_registry",
    "init_gateway_db",
    "router",
]
