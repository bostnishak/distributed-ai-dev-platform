"""GW-03, GW-04, GW-05, GW-06, GW-10: Model Registry, Explainable Selection, Context & VRAM Management."""

from __future__ import annotations

import json
import logging
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config
import db
import dbconn

_CTX_BUCKETS = (4096, 8192, 16384, 32768)

# PROC-08: Explicit license mapping mirrored with docs/plan-v2/model-licenses-ethics.md
KNOWN_MODEL_LICENSES: dict[str, str] = {
    "qwen": "Apache-2.0",
    "phi4": "MIT",
    "phi-4": "MIT",
    "llama3.2": "Llama 3.2 Community License",
    "llama3": "Llama 3 Community License",
    "gemma": "Gemma Terms of Use",
    "bge-m3": "MIT",
    "nomic-embed": "Apache-2.0",
    "mistral": "Apache-2.0",
}


def infer_model_license(name: str) -> str:
    low = (name or "").lower()
    for prefix, lic in KNOWN_MODEL_LICENSES.items():
        if prefix in low:
            return lic
    return "Open-Weights (Verify Upstream License)"

# Task dimension weights (mirrors task_weights.py for unified scoring across chat, studio & agents)
TASK_DIMENSION_WEIGHTS: dict[str, dict[str, float]] = {
    "kod": {"coding": 0.55, "reasoning": 0.25, "context": 0.10, "speed": 0.10},
    "code": {"coding": 0.55, "reasoning": 0.25, "context": 0.10, "speed": 0.10},
    "analiz": {"reasoning": 0.45, "context": 0.30, "structured_output": 0.15, "speed": 0.10},
    "long_doc": {"context": 0.55, "reasoning": 0.25, "structured_output": 0.10, "speed": 0.10},
    "research": {"reasoning": 0.45, "context": 0.30, "structured_output": 0.15, "speed": 0.10},
    "extract": {"structured_output": 0.55, "reasoning": 0.25, "coding": 0.10, "speed": 0.10},
    "genel": {"reasoning": 0.40, "coding": 0.20, "context": 0.20, "speed": 0.20},
    "short": {"speed": 0.50, "reasoning": 0.30, "coding": 0.10, "context": 0.10},
}


@dataclass
class ModelSelection:
    model: str
    provider: str
    node_id: str
    score: float
    reason: str
    warm: bool
    ctx_max: int


def _db_path() -> Path:
    p = Path(config.DATA_DIR) / "gateway.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(_db_path())


def init_registry_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS model_registry (
                name TEXT PRIMARY KEY,
                provider TEXT NOT NULL DEFAULT 'ollama',
                node_id TEXT NOT NULL DEFAULT 'master',
                param_size TEXT NOT NULL DEFAULT '',
                quantization TEXT NOT NULL DEFAULT '',
                context_length INTEGER NOT NULL DEFAULT 8192,
                capabilities_json TEXT NOT NULL DEFAULT '["completion"]',
                est_vram_gb REAL NOT NULL DEFAULT 4.0,
                scores_json TEXT NOT NULL DEFAULT '{}',
                hallucination_penalty REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'ready',
                warm INTEGER NOT NULL DEFAULT 0,
                override_json TEXT NOT NULL DEFAULT '{}',
                license TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(model_registry)")}
        if "license" not in cols:
            conn.execute("ALTER TABLE model_registry ADD COLUMN license TEXT NOT NULL DEFAULT ''")


def _infer_model_metadata(name: str, show_info: dict[str, Any] | None = None) -> dict[str, Any]:
    low = name.lower()
    caps = ["completion"]
    if any(k in low for k in ("embed", "bge-", "nomic", "mxbai")):
        caps = ["embedding"]
    if any(k in low for k in ("qwen3.5", "gemma4", "llava", "vision", "vl", "balloon")):
        caps.append("vision")
    if any(k in low for k in ("qwen", "llama3", "gemma", "phi4", "mistral")):
        caps.append("json")
        caps.append("tools")
    if "qwen3" in low or "r1" in low or "think" in low:
        caps.append("thinking")

    # Estimate parameter size & VRAM
    m_b = re.search(r"(\d+(?:\.\d+)?)b\b", low)
    params_b = float(m_b.group(1)) if m_b else (4.0 if "mini" in low or "e4b" in low else 7.0)
    est_vram = round(max(1.2, params_b * 0.72), 2)

    ctx_len = 8192
    if show_info:
        mi = show_info.get("model_info") or {}
        for k, v in mi.items():
            if "context_length" in str(k).lower() and isinstance(v, int) and v >= 1024:
                ctx_len = v
                break
        if isinstance(show_info.get("capabilities"), list) and show_info["capabilities"]:
            caps = sorted(set(caps + [str(c) for c in show_info["capabilities"]]))
    elif any(k in low for k in ("qwen3.5", "qwen2.5", "gemma4", "llama3.2")):
        ctx_len = 32768

    # Default capability profile scores (0-100) before benchmark overrides
    scores = {
        "coding": 88.0 if "coder" in low else (78.0 if params_b >= 7 else 66.0),
        "reasoning": 86.0 if params_b >= 8 else (76.0 if params_b >= 6 else 65.0),
        "context": min(95.0, 55.0 + math.log2(max(2048, ctx_len) / 2048) * 10.0),
        "structured_output": 85.0 if ("qwen" in low or "gemma4" in low) else 72.0,
        "speed": max(45.0, 95.0 - params_b * 4.0),
    }
    return {
        "param_size": f"{params_b:g}B",
        "context_length": ctx_len,
        "capabilities": sorted(set(caps)),
        "est_vram_gb": est_vram,
        "scores": scores,
        "hallucination_penalty": 0.0 if params_b >= 7 else 4.0,
    }


def upsert_model(
    name: str,
    *,
    provider: str = "ollama",
    node_id: str = "master",
    param_size: str = "",
    quantization: str = "",
    context_length: int = 8192,
    capabilities: list[str] | None = None,
    est_vram_gb: float = 4.0,
    scores: dict[str, float] | None = None,
    hallucination_penalty: float = 0.0,
    status: str = "ready",
    warm: bool = False,
    license_name: str = "",
) -> dict[str, Any]:
    init_registry_db()
    inferred = _infer_model_metadata(name)
    resolved_license = license_name.strip() or infer_model_license(name)
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO model_registry
                (name, provider, node_id, param_size, quantization, context_length, capabilities_json,
                 est_vram_gb, scores_json, hallucination_penalty, status, warm, license, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                provider = excluded.provider,
                node_id = excluded.node_id,
                param_size = CASE WHEN excluded.param_size != '' THEN excluded.param_size ELSE model_registry.param_size END,
                quantization = CASE WHEN excluded.quantization != '' THEN excluded.quantization ELSE model_registry.quantization END,
                context_length = excluded.context_length,
                capabilities_json = excluded.capabilities_json,
                est_vram_gb = excluded.est_vram_gb,
                scores_json = excluded.scores_json,
                hallucination_penalty = excluded.hallucination_penalty,
                status = excluded.status,
                warm = excluded.warm,
                license = CASE WHEN excluded.license != '' THEN excluded.license ELSE model_registry.license END,
                updated_at = excluded.updated_at
            """,
            (
                name,
                provider,
                node_id,
                param_size or inferred["param_size"],
                quantization,
                int(context_length or inferred["context_length"]),
                json.dumps(capabilities if capabilities is not None else inferred["capabilities"]),
                float(est_vram_gb or inferred["est_vram_gb"]),
                json.dumps(scores if scores is not None else inferred["scores"]),
                float(hallucination_penalty),
                status,
                int(bool(warm)),
                resolved_license,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM model_registry WHERE name = ?", (name,)).fetchone()
    return _row_to_model(row)


def _row_to_model(row: sqlite3.Row) -> dict[str, Any]:
    lic = ""
    if "license" in row.keys():
        lic = str(row["license"] or "")
    return {
        "name": row["name"],
        "provider": row["provider"],
        "node_id": row["node_id"],
        "param_size": row["param_size"],
        "quantization": row["quantization"],
        "context_length": int(row["context_length"]),
        "capabilities": json.loads(row["capabilities_json"] or '["completion"]'),
        "est_vram_gb": float(row["est_vram_gb"]),
        "scores": json.loads(row["scores_json"] or "{}"),
        "hallucination_penalty": float(row["hallucination_penalty"]),
        "status": row["status"],
        "warm": bool(row["warm"]),
        "license": lic or infer_model_license(row["name"]),
        "updated_at": row["updated_at"],
    }


def list_models() -> list[dict[str, Any]]:
    init_registry_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM model_registry ORDER BY warm DESC, name ASC").fetchall()
    return [_row_to_model(r) for r in rows]


async def sync_from_ollama(ollama_provider: Any) -> list[dict[str, Any]]:
    """Sync model_registry from Ollama `/api/tags`, `/api/show`, `/api/ps`, and registered agents."""
    init_registry_db()
    tags = await ollama_provider.list_tags()
    warm_names: set[str] = set()
    try:
        running = await ollama_provider.list_running()
        warm_names = {str(m.get("name") or "") for m in running}
    except Exception as exc:
        logging.getLogger(__name__).debug('registry call skipped: %s', exc)

    synced: list[dict[str, Any]] = []
    for item in tags:
        mname = str(item.get("name") or "").strip()
        if not mname:
            continue
        details = item.get("details") or {}
        show_info: dict[str, Any] = {}
        try:
            show_info = await ollama_provider.show_model(mname)
        except Exception as exc:
            logging.getLogger(__name__).debug('registry detail skipped: %s', exc)
        meta = _infer_model_metadata(mname, show_info=show_info)
        rec = upsert_model(
            mname,
            provider="ollama",
            node_id="master",
            param_size=str(details.get("parameter_size") or meta["param_size"]),
            quantization=str(details.get("quantization_level") or ""),
            context_length=int(meta["context_length"]),
            capabilities=meta["capabilities"],
            est_vram_gb=meta["est_vram_gb"],
            scores=meta["scores"],
            hallucination_penalty=meta["hallucination_penalty"],
            status="ready",
            warm=(mname in warm_names),
        )
        synced.append(rec)

    # Also merge benchmark scores from distributed agents if registered
    try:
        for agent in db.list_agents():
            mname = str(agent.get("model") or "")
            if not mname:
                continue
            sc = db.get_agent_scores(agent["agent_id"]).get("latest") or {}
            if sc:
                scores_map = {dim: float(info["score"]) for dim, info in sc.items()}
                upsert_model(
                    mname,
                    provider="agent",
                    node_id=agent["agent_id"],
                    context_length=int(agent.get("context_length") or 8192),
                    capabilities=list(agent.get("capabilities") or ["completion"]),
                    scores=scores_map,
                )
    except Exception as exc:
        logging.getLogger(__name__).debug("registry sync metadata skipped: %s", exc)
    return synced


def select_model(
    task_type: str = "genel",
    *,
    required_ctx: int = 2048,
    require_vision: bool = False,
    require_tools: bool = False,
    prefer_warm: bool = True,
    fallback_model: str | None = None,
) -> ModelSelection:
    """GW-04 & GW-10: Explainable capability-based model selection with warm-model & context scoring."""
    models = [m for m in list_models() if m["status"] == "ready" and "embedding" not in m["capabilities"]]
    if not models:
        fb = fallback_model or config.MASTER_MODEL
        return ModelSelection(
            model=fb,
            provider="ollama",
            node_id="master",
            score=50.0,
            reason=f"Kayıt defteri boş; varsayılan yerel model ({fb}) seçildi.",
            warm=False,
            ctx_max=8192,
        )

    weights = TASK_DIMENSION_WEIGHTS.get(task_type, TASK_DIMENSION_WEIGHTS["genel"])
    best: tuple[float, dict[str, Any], str] | None = None

    for m in models:
        caps = set(m["capabilities"])
        if require_vision and "vision" not in caps:
            continue
        if require_tools and "tools" not in caps:
            continue
        scores = m["scores"] or {}
        base = sum(weights.get(dim, 0.0) * float(scores.get(dim, 60.0)) for dim in weights)
        ctx_bonus = 6.0 if m["context_length"] >= required_ctx else -45.0
        warm_bonus = 5.0 if (prefer_warm and m["warm"]) else 0.0
        penalty = float(m.get("hallucination_penalty") or 0.0)
        total = round(base + ctx_bonus + warm_bonus - penalty, 2)
        reason = (
            f"görev={task_type}, temel_skor={base:.1f}, bağlam={m['context_length']} (gereken {required_ctx}), "
            f"sıcak={'evet' if m['warm'] else 'hayır'}, halüsinasyon_cezası=-{penalty:.1f}"
        )
        if best is None or total > best[0]:
            best = (total, m, reason)

    if best is None:
        m = models[0]
        return ModelSelection(
            model=m["name"],
            provider=m["provider"],
            node_id=m["node_id"],
            score=40.0,
            reason=f"Kısıtları tam karşılayan model yok; en yakın aday ({m['name']}) seçildi.",
            warm=m["warm"],
            ctx_max=m["context_length"],
        )

    sc_val, chosen, why = best
    return ModelSelection(
        model=chosen["name"],
        provider=chosen["provider"],
        node_id=chosen["node_id"],
        score=sc_val,
        reason=why,
        warm=chosen["warm"],
        ctx_max=chosen["context_length"],
    )


# ---------------------------------------------------------------- GW-05 & GW-06 Context Window & Dynamic num_ctx

def estimate_tokens(text_or_messages: str | list[dict[str, Any]]) -> int:
    """Conservative tokenizer estimator (~3.4 chars/token for Turkish/mixed code) so context never overflows."""
    if isinstance(text_or_messages, str):
        return max(1, math.ceil(len(text_or_messages) / 3.4))
    total_chars = sum(len(str(m.get("content") or "")) + 16 for m in text_or_messages)
    return max(1, math.ceil(total_chars / 3.4))


def choose_dynamic_num_ctx(used_tokens: int, model_max_ctx: int = 32768) -> int:
    """GW-06: Snap num_ctx to 4k/8k/16k/32k buckets to prevent unnecessary Ollama model reloads."""
    needed = int(used_tokens * 1.35) + 512
    cap = max(4096, int(model_max_ctx or 8192))
    for bucket in _CTX_BUCKETS:
        if bucket >= needed and bucket <= cap:
            return bucket
    return min(cap, _CTX_BUCKETS[-1])


def plan_context_strategy(used_tokens: int, ctx_max: int) -> dict[str, Any]:
    """GW-05: Decide overflow strategy (direct -> rag -> summarize -> map_reduce) transparently."""
    ratio = used_tokens / max(1, ctx_max)
    if ratio <= 0.78:
        strategy = "direct"
    elif ratio <= 1.25:
        strategy = "rag"
    elif ratio <= 2.2:
        strategy = "summarize"
    else:
        strategy = "map_reduce"
    return {
        "ctx_used": used_tokens,
        "ctx_max": ctx_max,
        "overflow": ratio > 0.78,
        "strategy": strategy,
    }


def fit_messages_to_context(
    messages: list[dict[str, Any]],
    ctx_max: int,
    *,
    reserve_output: int = 1024,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Trim/summarize conversation history deterministically so messages NEVER exceed `ctx_max`."""
    budget = max(1024, ctx_max - reserve_output)
    used = estimate_tokens(messages)
    plan = plan_context_strategy(used, budget)
    if used <= budget:
        return messages, {**plan, "ctx_used": used, "ctx_max": ctx_max}

    # Always preserve system prompt (first) and latest user prompt (last)
    sys_msgs = [m for m in messages[:1] if m.get("role") == "system"]
    tail = messages[-1:] if messages else []
    middle = messages[len(sys_msgs) : -1] if len(messages) > len(sys_msgs) + 1 else []

    # Summarize/drop oldest middle turns until within budget
    kept_mid: list[dict[str, Any]] = []
    running = estimate_tokens(sys_msgs + tail)
    for m in reversed(middle):
        cost = estimate_tokens([m])
        if running + cost <= budget:
            kept_mid.insert(0, m)
            running += cost
        else:
            break

    # If still over budget (giant single user prompt), truncate tail safely to fit
    final_msgs = sys_msgs + kept_mid + tail
    if estimate_tokens(final_msgs) > budget and final_msgs:
        max_chars = max(512, int((budget - estimate_tokens(sys_msgs)) * 3.0))
        last = dict(final_msgs[-1])
        last["content"] = str(last.get("content") or "")[:max_chars] + "\n[... bağlam penceresi sınırı nedeniyle kısaltıldı ...]"
        final_msgs[-1] = last

    final_used = estimate_tokens(final_msgs)
    return final_msgs, {**plan, "ctx_used": final_used, "ctx_max": ctx_max}
