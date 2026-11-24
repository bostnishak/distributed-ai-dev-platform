"""GW-07..GW-15 helpers: Decoding profiles, classified errors, circuit breaker, cancellation & SQLite traces."""

from __future__ import annotations

import asyncio
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

import config
from gateway import registry as gw_registry
from log_sanitizer import redact_sensitive_text
from prompt_loader import load_prompt

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

@dataclass
class CallTraceRecord:
    run_id: str
    user_id: str
    feature: str
    template_version: str
    provider: str
    model: str
    profile: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    status: str = "ok"
    error: str = ""
    prompt_summary: str = ""
    response_summary: str = ""


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


@dataclass
class ChatCallOptions:
    model: str | None = None
    provider_name: str | None = None
    task_type: str = "genel"
    profile: str | None = None
    fallback_models: list[str] | None = None
    user_id: str = "default"
    run_id: str | None = None
    feature: str = "chat"
    template_version: str = ""
    use_cache: bool = False
    private_user_data: bool = True
    format_schema: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    seed: int | None = None
    num_predict: int | None = None
    num_ctx: int | None = None
    max_retries: int = 2
    cancel_token: CancellationToken | None = None
    timeout_s: float = 120.0

    @classmethod
    def from_kwargs(cls, kwargs: dict[str, Any]) -> ChatCallOptions:
        return cls(
            model=kwargs.get("model"),
            provider_name=kwargs.get("provider_name"),
            task_type=str(kwargs.get("task_type", "genel")),
            profile=kwargs.get("profile"),
            fallback_models=kwargs.get("fallback_models"),
            user_id=str(kwargs.get("user_id", "default")),
            run_id=kwargs.get("run_id"),
            feature=str(kwargs.get("feature", "chat")),
            template_version=str(kwargs.get("template_version", "")),
            use_cache=bool(kwargs.get("use_cache", False)),
            private_user_data=bool(kwargs.get("private_user_data", True)),
            format_schema=kwargs.get("format_schema"),
            tools=kwargs.get("tools"),
            seed=kwargs.get("seed"),
            num_predict=kwargs.get("num_predict"),
            num_ctx=kwargs.get("num_ctx"),
            max_retries=int(kwargs.get("max_retries", 2)),
            cancel_token=kwargs.get("cancel_token"),
            timeout_s=float(kwargs.get("timeout_s", 120.0)),
        )


_INITIALIZED_GW_PATHS: set[str] = set()


def gw_db_path() -> Path:
    p = Path(config.DATA_DIR) / "gateway.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def gw_conn() -> sqlite3.Connection:
    import dbconn

    p = gw_db_path()
    conn = dbconn.open_db(p)
    key = str(p.resolve())
    if key not in _INITIALIZED_GW_PATHS:
        conn.executescript(load_prompt("b1_gateway_schema.txt"))
        _INITIALIZED_GW_PATHS.add(key)
    return conn


def init_gateway_db() -> None:
    gw_registry.init_registry_db()
    with gw_conn() as conn:
        conn.executescript(load_prompt("b1_gateway_schema.txt"))


def record_call(rec: CallTraceRecord) -> str:
    init_gateway_db()
    tid = f"trc-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    with gw_conn() as conn:
        conn.execute(
            """
            INSERT INTO llm_calls
                (trace_id, run_id, user_id, feature, template_version, provider, model, profile,
                 tokens_in, tokens_out, latency_ms, status, error, prompt_summary, response_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tid,
                rec.run_id or tid,
                rec.user_id,
                rec.feature,
                rec.template_version,
                rec.provider,
                rec.model,
                rec.profile,
                rec.tokens_in,
                rec.tokens_out,
                rec.latency_ms,
                rec.status,
                redact_sensitive_text(rec.error)[:300],
                redact_sensitive_text(rec.prompt_summary)[:160],
                redact_sensitive_text(rec.response_summary)[:160],
                now,
            ),
        )
    return tid


def get_run_traces(run_id: str) -> list[dict[str, Any]]:
    init_gateway_db()
    with gw_conn() as conn:
        rows = conn.execute("SELECT * FROM llm_calls WHERE run_id = ? ORDER BY created_at ASC", (run_id,)).fetchall()
    return [dict(r) for r in rows]


def daily_user_tokens(user_id: str) -> int:
    init_gateway_db()
    today_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
    with gw_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) AS tot FROM llm_calls WHERE user_id = ? AND created_at LIKE ?",
            (user_id, f"{today_prefix}%"),
        ).fetchone()
    return int(row["tot"] or 0) if row else 0


async def execute_council_chat(client: Any, prompt: str, **opts: Any) -> dict[str, Any]:
    """GW-18: Multi-model proposer -> critic -> judge council orchestration."""
    proposer_models: list[str] = list(opts["proposer_models"])
    critic_model = str(opts["critic_model"])
    judge_model = str(opts["judge_model"])
    provider_name: str | None = opts.get("provider_name")
    user_id = str(opts.get("user_id", "default"))
    rid = f"cnl-{uuid.uuid4().hex[:10]}"

    async def _propose(m: str) -> dict[str, Any]:
        res = await client.chat(
            [{"role": "user", "content": prompt}],
            model=m,
            provider_name=provider_name,
            task_type="analiz",
            profile="analytic",
            user_id=user_id,
            run_id=rid,
            feature="council_proposer",
        )
        return {"model": res.model, "answer": res.content, "latency_ms": res.latency_ms}

    proposals = list(await asyncio.gather(*(_propose(m) for m in proposer_models)))
    joined = "\n\n".join(f"[{p['model']}]:\n{p['answer']}" for p in proposals)
    critic = await client.chat(
        [{"role": "user", "content": f"Soru: {prompt}\n\nÖneriler:\n{joined}\n\nÇelişkileri, hataları ve eksik kanıtları listele."}],
        model=critic_model,
        provider_name=provider_name,
        task_type="analiz",
        profile="factual",
        user_id=user_id,
        run_id=rid,
        feature="council_critic",
    )
    judge = await client.chat(
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


async def execute_cascade_chat(client: Any, messages: list[dict[str, Any]], **opts: Any) -> dict[str, Any]:
    """GW-19: FrugalGPT-style cascade: fast small model first, escalate only on low confidence."""
    fast_model = str(opts["fast_model"])
    strong_model = str(opts["strong_model"])
    confidence_threshold = float(opts.get("confidence_threshold", 0.72))
    provider_name: str | None = opts.get("provider_name")
    user_id = str(opts.get("user_id", "default"))
    run_id: str | None = opts.get("run_id")

    first = await client.chat(
        messages,
        model=fast_model,
        provider_name=provider_name,
        task_type="short",
        profile="factual",
        user_id=user_id,
        run_id=run_id,
        feature="cascade_fast",
    )
    low = first.content.lower()
    uncertain = any(k in low for k in ("emin değilim", "bilmiyorum", "tahmin", "belirsiz", "not sure")) or len(first.content.strip()) < 12
    conf = 0.45 if uncertain else 0.88
    if conf >= confidence_threshold:
        return {"escalated": False, "confidence": conf, "result": first}

    strong = await client.chat(
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


async def compute_gateway_status(client: Any) -> dict[str, Any]:
    """GW-20: Live gateway health, warm models, queue depth, circuit breakers, and 5-min error rate."""
    from gateway.providers import OllamaProvider

    ollama_ok = False
    reason = ""
    warm_models: list[str] = []
    if "ollama" in client.providers and isinstance(client.providers["ollama"], OllamaProvider):
        try:
            running = await client.providers["ollama"].list_running()
            warm_models = [str(m.get("name") or "") for m in running]
            ollama_ok = True
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            reason = f"Ollama erişilemiyor: {exc}"

    cutoff = datetime.fromtimestamp(time.time() - 300, tz=UTC).isoformat()
    with gw_conn() as conn:
        tot = conn.execute("SELECT COUNT(*) AS c FROM llm_calls WHERE created_at >= ?", (cutoff,)).fetchone()["c"]
        errs = conn.execute("SELECT COUNT(*) AS c FROM llm_calls WHERE created_at >= ? AND status='error'", (cutoff,)).fetchone()["c"]

    return {
        "status": "healthy" if ollama_ok else "degraded",
        "reason": reason or "Tüm yerel sağlayıcılar hazır",
        "providers": sorted(client.providers.keys()),
        "warm_models": warm_models,
        "registered_models": len(gw_registry.list_models()),
        "active_queue_depth": client._active_requests,
        "error_rate_5m": round((errs / tot), 3) if tot else 0.0,
        "circuit_breakers": client.breaker.snapshot(),
        "cache": {"hits": client._cache_hits, "misses": client._cache_misses},
    }
