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
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

import config
from gateway import prompts as gw_prompts
from gateway import registry as gw_registry
from gateway.client_helpers import (
    DECODING_PROFILES,
    TASK_TO_PROFILE,
    BudgetExceededError,
    CallTraceRecord,
    CancellationToken,
    ChatCallOptions,
    ChatResult,
    CircuitBreaker,
    ConnectionFailedError,
    ContextOverflowError,
    GatewayError,
    ModelNotFoundError,
    OOMError,
    TimeoutFailureError,
    classify_error,
    daily_user_tokens,
    get_run_traces,
    gw_conn,
    gw_db_path,
    init_gateway_db,
    record_call,
)
from gateway.providers import (
    OllamaProvider,
    Provider,
    ProviderResponse,
    load_optional_cloud_providers,
)

log = logging.getLogger("gateway.client")
router = APIRouter(prefix="/api/gateway", tags=["gateway"])

TModel = TypeVar("TModel", bound=BaseModel)

_gw_db_path = gw_db_path
_gw_conn = gw_conn
_daily_user_tokens = daily_user_tokens


@dataclass
class _PreparedChat:
    rid: str
    prof: str
    est_in: int
    sel: gw_registry.ModelSelection
    chosen_model: str
    chosen_prov: str
    fitted_msgs: list[dict[str, Any]]
    ctx_info: dict[str, Any]
    decoding_opts: dict[str, Any]
    cache_key: str


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
        self.daily_token_budget: int = 0
        init_gateway_db()

    def register_provider(self, provider: Provider) -> None:
        self.providers[provider.name] = provider

    def _get_provider(self, name: str) -> Provider:
        if name not in self.providers:
            raise GatewayError(f"Sağlayıcı yüklü değil veya kapalı: {name}")
        return self.providers[name]

    def _check_budget(self, user_id: str) -> None:
        if self.daily_token_budget > 0:
            used = daily_user_tokens(user_id)
            if used >= self.daily_token_budget:
                raise BudgetExceededError(
                    f"Günlük token bütçesi aşıldı ({used}/{self.daily_token_budget})."
                )

    def _cache_key(self, model: str, profile: str, payload: Any) -> str:
        raw = json.dumps({"m": model, "p": profile, "x": payload}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> Any | None:
        with gw_conn() as conn:
            row = conn.execute("SELECT value_json, expires_at FROM llm_cache WHERE cache_key = ?", (key,)).fetchone()
        if not row or float(row["expires_at"]) < time.time():
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return json.loads(row["value_json"])

    def _cache_put(self, key: str, model: str, profile: str, value: Any, ttl_s: float = 3600.0) -> None:
        with gw_conn() as conn:
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
        base["num_predict"] = (num_predict or config.ASSISTANT_NUM_PREDICT)
        if seed is not None:
            base["seed"] = seed
        return base

    def _prepare_chat(self, messages: list[dict[str, Any]], call: ChatCallOptions) -> _PreparedChat:
        rid = call.run_id or f"run-{uuid.uuid4().hex[:10]}"
        prof = call.profile or TASK_TO_PROFILE.get(call.task_type, "analytic")
        est_in = gw_registry.estimate_tokens(messages)
        sel = gw_registry.select_model(task_type=call.task_type, required_ctx=est_in + 512, fallback_model=call.model)
        chosen_model = call.model or sel.model
        chosen_prov = call.provider_name or sel.provider
        if chosen_prov not in self.providers:
            chosen_prov = next(iter(self.providers))
        fitted_msgs, ctx_info = gw_registry.fit_messages_to_context(messages, sel.ctx_max)
        num_ctx = call.num_ctx if call.num_ctx and call.num_ctx > 0 else gw_registry.choose_dynamic_num_ctx(ctx_info["ctx_used"], sel.ctx_max, call.num_predict or config.ASSISTANT_NUM_PREDICT)
        decoding_opts = self._build_options(prof, num_ctx, num_predict=call.num_predict, seed=call.seed)
        cache_key = ""
        if call.use_cache and not call.private_user_data and not call.tools:
            cache_key = self._cache_key(chosen_model, prof, {"msgs": fitted_msgs, "schema": call.format_schema})
        return _PreparedChat(rid, prof, est_in, sel, chosen_model, chosen_prov, fitted_msgs, ctx_info, decoding_opts, cache_key)

    def _lookup_chat_cache(self, prep: _PreparedChat, call: ChatCallOptions) -> ChatResult | None:
        if not prep.cache_key:
            return None
        hit = self._cache_get(prep.cache_key)
        if hit is None:
            return None
        content = str(hit.get("content") or "")
        tid = record_call(
            CallTraceRecord(
                run_id=prep.rid,
                user_id=call.user_id,
                feature=call.feature,
                template_version=call.template_version,
                provider=prep.chosen_prov,
                model=prep.chosen_model,
                profile=prep.prof,
                status="cached",
                prompt_summary=str(prep.fitted_msgs[-1].get("content") or ""),
                response_summary=content,
            )
        )
        return ChatResult(
            content=content,
            model=prep.chosen_model,
            provider=prep.chosen_prov,
            node_id="cache",
            profile=prep.prof,
            trace_id=tid,
            run_id=prep.rid,
            cached=True,
            selection_reason=prep.sel.reason,
            context_info=prep.ctx_info,
        )

    def _finalize_chat_success(
        self,
        prep: _PreparedChat,
        call: ChatCallOptions,
        res: ProviderResponse,
        fallback_note: str,
    ) -> ChatResult:
        if prep.cache_key:
            self._cache_put(prep.cache_key, res.model, prep.prof, {"content": res.content})
        tok_in = res.tokens_in or prep.est_in
        tok_out = res.tokens_out or gw_registry.estimate_tokens(res.content)
        tid = record_call(
            CallTraceRecord(
                run_id=prep.rid,
                user_id=call.user_id,
                feature=call.feature,
                template_version=call.template_version,
                provider=res.provider,
                model=res.model,
                profile=prep.prof,
                tokens_in=tok_in,
                tokens_out=tok_out,
                latency_ms=res.latency_ms,
                status="ok",
                prompt_summary=str(prep.fitted_msgs[-1].get("content") or ""),
                response_summary=res.content,
            )
        )
        return ChatResult(
            content=res.content,
            model=res.model,
            provider=res.provider,
            node_id=res.node_id,
            profile=prep.prof,
            trace_id=tid,
            run_id=prep.rid,
            tokens_in=tok_in,
            tokens_out=tok_out,
            latency_ms=res.latency_ms,
            fallback_note=fallback_note,
            selection_reason=prep.sel.reason,
            context_info=prep.ctx_info,
            tool_calls=res.tool_calls,
        )

    async def _try_candidate_model(
        self,
        prep: _PreparedChat,
        call: ChatCallOptions,
        cand_model: str,
        cand_idx: int,
    ) -> tuple[ChatResult | None, GatewayError | None]:
        cb_key = f"{prep.chosen_prov}:{cand_model}"
        if self.breaker.is_open(cb_key):
            return None, None
        prov = self._get_provider(prep.chosen_prov)
        last_err: GatewayError | None = None
        for attempt in range(call.max_retries + 1):
            if call.cancel_token:
                call.cancel_token.check()
            try:
                res: ProviderResponse = await prov.chat(
                    cand_model,
                    prep.fitted_msgs,
                    dict(prep.decoding_opts),
                    format_schema=call.format_schema,
                    tools=call.tools,
                    timeout_s=call.timeout_s,
                )
                self.breaker.record_success(cb_key)
                note = f"{prep.chosen_model} yüklenemedi, {cand_model} kullanıldı." if cand_idx > 0 else ""
                return self._finalize_chat_success(prep, call, res, note), None
            except asyncio.CancelledError:
                raise
            except (
                httpx.HTTPError,
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                LookupError,
                AttributeError,
                sqlite3.Error,
            ) as exc:
                last_err = classify_error(exc)
                self.breaker.record_failure(cb_key)
                if isinstance(last_err, (ModelNotFoundError, OOMError)):
                    break
                if attempt < call.max_retries:
                    await asyncio.sleep(0.15 * (2**attempt))
        return None, last_err

    async def chat(self, messages: list[dict[str, Any]], **opts: Any) -> ChatResult:
        call = ChatCallOptions.from_kwargs(opts)
        self._check_budget(call.user_id)
        if call.cancel_token:
            call.cancel_token.check()
        prep = self._prepare_chat(messages, call)
        cached = self._lookup_chat_cache(prep, call)
        if cached is not None:
            return cached

        candidates = [prep.chosen_model, *(call.fallback_models or [])]
        last_err: GatewayError | None = None
        async with self._sem:
            self._active_requests += 1
            try:
                for cand_idx, cand_model in enumerate(candidates):
                    result, cand_err = await self._try_candidate_model(prep, call, cand_model, cand_idx)
                    if result is not None:
                        return result
                    if cand_err is not None:
                        last_err = cand_err
            finally:
                self._active_requests = max(0, self._active_requests - 1)

        err = last_err or GatewayError("Tüm aday modeller başarısız oldu.")
        record_call(
            CallTraceRecord(
                run_id=prep.rid,
                user_id=call.user_id,
                feature=call.feature,
                template_version=call.template_version,
                provider=prep.chosen_prov,
                model=prep.chosen_model,
                profile=prep.prof,
                status="error",
                error=str(err),
                prompt_summary=str(prep.fitted_msgs[-1].get("content") or ""),
            )
        )
        raise err

    async def stream(self, messages: list[dict[str, Any]], **opts: Any) -> AsyncIterator[dict[str, Any]]:
        call = ChatCallOptions.from_kwargs({"timeout_s": 180.0, **opts})
        self._check_budget(call.user_id)
        prep = self._prepare_chat(messages, call)
        prov = self._get_provider(prep.chosen_prov)

        t0 = time.perf_counter()
        acc: list[str] = []
        tok_in, tok_out = prep.est_in, 0
        try:
            async for evt in prov.stream(prep.chosen_model, prep.fitted_msgs, prep.decoding_opts, timeout_s=call.timeout_s):
                if call.cancel_token and call.cancel_token.cancelled:
                    break
                if evt.get("type") == "token":
                    acc.append(str(evt.get("content") or ""))
                elif evt.get("type") == "done":
                    tok_in = int(evt.get("tokens_in") or prep.est_in)
                    tok_out = int(evt.get("tokens_out") or gw_registry.estimate_tokens("".join(acc)))
                    evt["ctx_info"] = prep.ctx_info
                    evt["selection_reason"] = prep.sel.reason
                    evt["run_id"] = prep.rid
                yield evt
            record_call(
                CallTraceRecord(
                    run_id=prep.rid,
                    user_id=call.user_id,
                    feature="stream",
                    template_version="",
                    provider=prep.chosen_prov,
                    model=prep.chosen_model,
                    profile=prep.prof,
                    tokens_in=tok_in,
                    tokens_out=tok_out,
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    status="cancelled" if (call.cancel_token and call.cancel_token.cancelled) else "ok",
                    prompt_summary=str(prep.fitted_msgs[-1].get("content") or ""),
                    response_summary="".join(acc),
                )
            )
        except Exception as exc:
            err = classify_error(exc)
            record_call(
                CallTraceRecord(
                    run_id=prep.rid,
                    user_id=call.user_id,
                    feature="stream",
                    template_version="",
                    provider=prep.chosen_prov,
                    model=prep.chosen_model,
                    profile=prep.prof,
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    status="error",
                    error=str(err),
                )
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
        **opts: Any,
    ) -> TModel:
        """GW-11: Schema-constrained JSON generation with Pydantic validation and up to 2 repair retries."""
        model: str | None = opts.get("model")
        provider_name: str | None = opts.get("provider_name")
        max_repairs = int(opts.get("max_repairs", 2))
        user_id = str(opts.get("user_id", "default"))
        run_id: str | None = opts.get("run_id")

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
        **opts: Any,
    ) -> dict[str, Any]:
        """GW-12: Unified tool calling — native Ollama `tools` OR schema-constrained ReAct JSON fallback."""
        model: str | None = opts.get("model")
        provider_name: str | None = opts.get("provider_name")
        native_tools_supported = bool(opts.get("native_tools_supported", True))
        user_id = str(opts.get("user_id", "default"))
        run_id: str | None = opts.get("run_id")

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

        class ReActDecision(BaseModel):
            action: str
            arguments: dict[str, Any] = {}
            final_answer: str = ""

        tool_desc = json.dumps(
            [{"name": t["function"]["name"], "desc": t["function"].get("description", "")} for t in tools],
            ensure_ascii=False,
        )
        react_msgs = [
            *messages,
            {"role": "system", "content": f"Kullanılabilir araçlar: {tool_desc}. Araç çağıracaksan action alanına araç adını, bitiriyorsan action='final' yaz."},
        ]
        dec = await self.structured(react_msgs, ReActDecision, model=model, provider_name=provider_name, user_id=user_id, run_id=run_id)
        if dec.action != "final":
            return {"type": "tool_call", "name": dec.action, "arguments": dec.arguments, "model": model or ""}
        return {"type": "final", "content": dec.final_answer, "model": model or ""}

    async def run_council(self, prompt: str, **opts: Any) -> dict[str, Any]:
        """GW-18: Multi-model independent proposer -> critic -> judge synthesis with disagreement tracking."""
        from gateway.client_helpers import execute_council_chat

        return await execute_council_chat(self, prompt, **opts)

    async def cascade_chat(self, messages: list[dict[str, Any]], **opts: Any) -> dict[str, Any]:
        """GW-19: FrugalGPT-style cascade: try fast small model first; escalate only if confidence < threshold."""
        from gateway.client_helpers import execute_cascade_chat

        return await execute_cascade_chat(self, messages, **opts)

    async def gateway_status(self) -> dict[str, Any]:
        """GW-20: Live gateway health, warm models, queue depth, circuit breakers, and 5-min error rate."""
        from gateway.client_helpers import compute_gateway_status

        return await compute_gateway_status(self)


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
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, sqlite3.Error) as exc:
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
