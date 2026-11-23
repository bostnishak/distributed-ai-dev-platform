"""Feature flags: anything not proven stays off (OPS-11).

A flag has a global default stored in ``feature_flags`` and optional per-user overrides. Experimental
capabilities (council, chain-of-verification, graph RAG, image generation) are registered here as *off*, and a
flag is only switched on once an evaluation shows it helps. Changes go to the audit trail.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import config
import dbconn

log = logging.getLogger(__name__)

KNOWN_FLAGS: dict[str, tuple[bool, str]] = {
    "reasoning_council": (False, "Çok modelli tartışma konseyi (GW-18); yalnız eval'de kazanç gösterirse açılır"),
    "chain_of_verification": (False, "Doğrulama zinciri (HAL-10)"),
    "self_consistency": (False, "Öz-tutarlılık örnekleme (HAL-11)"),
    "graph_rag": (False, "Bilgi grafı destekli getirme (RAG-17)"),
    "web_search": (False, "Web araması ve sayfa okuma (RAG-18); ağ erişimi gerektirir"),
    "image_diffusion": (False, "Yerel difüzyon ile görsel üretimi (MM-05)"),
    "cloud_providers": (False, "Harici bulut LLM sağlayıcıları (karar D1); varsayılan kapalı"),
    "adapter_promotion": (False, "Eğitilmiş adaptörün otomatik canlıya alınması (ML-08)"),
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ensure_registered() -> None:
    """Make sure every known flag has a row; existing rows (and their state) are left alone."""
    with dbconn.connection(config.DB_PATH) as conn:
        for name, (default, description) in KNOWN_FLAGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO feature_flags (name, enabled, description, updated_at) VALUES (?, ?, ?, ?)",
                (name, int(default), description, _now()),
            )


def is_enabled(name: str, owner: str | None = None) -> bool:
    """Unknown flags are off. A user override wins over the global value."""
    if name not in KNOWN_FLAGS:
        return False
    with dbconn.connection(config.DB_PATH) as conn:
        if owner:
            row = conn.execute(
                "SELECT enabled FROM feature_overrides WHERE name = ? AND feature_overrides.owner_id = ?", (name, owner)
            ).fetchone()
            if row is not None:
                return bool(row[0])
        row = conn.execute("SELECT enabled FROM feature_flags WHERE name = ?", (name,)).fetchone()
    return bool(row[0]) if row is not None else KNOWN_FLAGS[name][0]


def set_flag(name: str, enabled: bool, actor: str = "admin", owner: str | None = None) -> None:
    if name not in KNOWN_FLAGS:
        raise KeyError(name)
    ensure_registered()
    with dbconn.connection(config.DB_PATH) as conn:
        if owner:
            conn.execute(
                "INSERT INTO feature_overrides (name, owner_id, enabled) VALUES (?, ?, ?) "
                "ON CONFLICT(name, owner_id) DO UPDATE SET enabled = excluded.enabled", (name, owner, int(enabled)))
        else:
            conn.execute("UPDATE feature_flags SET enabled = ?, updated_at = ?, updated_by = ? WHERE name = ?",
                         (int(enabled), _now(), actor, name))
    try:
        from audit_log import AuditTrail

        AuditTrail().append_event(actor=actor, action="FEATURE_FLAG_CHANGED",
                                  payload={"name": name, "enabled": enabled, "owner": owner})
    except Exception:
        log.warning("bayrak değişikliği denetim izine yazılamadı", exc_info=True)


def snapshot(owner: str | None = None) -> dict[str, dict]:
    ensure_registered()
    return {name: {"enabled": is_enabled(name, owner), "description": desc} for name, (_d, desc) in KNOWN_FLAGS.items()}
