"""Group unhandled exceptions so one recurring bug is one row with a count (OPS-19).

The fingerprint is the exception type, the route template and the innermost stack frame (file and function,
not line number), so the same bug groups together across deploys. Only the message head and a trimmed
traceback are kept, and both pass through the log redactor first.
"""

from __future__ import annotations

import hashlib
import logging
import traceback
from datetime import UTC, datetime

import config
import dbconn
import metrics

log = logging.getLogger(__name__)
MAX_MESSAGE = 300
MAX_SAMPLE = 4000


def fingerprint(exc: BaseException, route: str | None) -> str:
    frames = traceback.extract_tb(exc.__traceback__)
    where = f"{frames[-1].filename.replace(chr(92), '/').rsplit('/', 1)[-1]}:{frames[-1].name}" if frames else "?"
    raw = f"{type(exc).__name__}|{route or '-'}|{where}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _mask(text: str) -> str:
    try:
        import log_sanitizer

        return log_sanitizer.redact_sensitive_text(text)
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
        return text


def record(exc: BaseException, route: str | None = None, request_id: str | None = None) -> str | None:
    """Store or count the error; never raises, because it runs while another failure is being handled."""
    try:
        kind = type(exc).__name__
        message = _mask(str(exc))[:MAX_MESSAGE]
        sample = _mask("".join(traceback.format_exception(exc)))[-MAX_SAMPLE:]
        key = fingerprint(exc, route)
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with dbconn.connection(config.DB_PATH) as conn:
            conn.execute(
                "INSERT INTO error_events (fingerprint, kind, message, route, sample, count, first_seen, last_seen, "
                "request_id) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?) ON CONFLICT(fingerprint) DO UPDATE SET "
                "count = count + 1, last_seen = excluded.last_seen, request_id = excluded.request_id",
                (key, kind, message, route, sample, now, now, request_id),
            )
        metrics.inc("errors_total", kind=kind)
        return key
    except Exception:
        log.warning("hata kaydı yazılamadı", exc_info=True)
        return None


def recent(limit: int = 50) -> list[dict]:
    with dbconn.connection(config.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT fingerprint, kind, message, route, count, first_seen, last_seen, request_id "
            "FROM error_events ORDER BY last_seen DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
    return [dict(r) for r in rows]


def prune(older_than_days: int = 30) -> int:
    from datetime import timedelta

    cutoff = (datetime.now(UTC) - timedelta(days=older_than_days)).isoformat(timespec="seconds")
    with dbconn.connection(config.DB_PATH) as conn:
        return conn.execute("DELETE FROM error_events WHERE last_seen < ?", (cutoff,)).rowcount
