"""Structured JSON logging with a request id on every line (OPS-01).

One request, one ``request_id``: every log line written while it is handled carries it, so a failure in the
log can be followed back to the request that caused it. Secrets and personal data are masked by the filter
from ``log_sanitizer`` before a line is written.
"""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from pathlib import Path

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")

_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "request_id", "run_id"}


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.run_id = run_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "run_id": getattr(record, "run_id", "-"),
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD and not k.startswith("_")}
        if extra:
            entry["extra"] = extra
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure(level: str = "INFO", json_output: bool = True, log_file: Path | None = None) -> None:
    """Replace the root handlers with ours; safe to call more than once."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_cm6453", False):
            root.removeHandler(handler)
    formatter: logging.Formatter = JsonFormatter() if json_output else logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"))
    redactor = _redaction_filter()
    for handler in handlers:
        handler._cm6453 = True  # type: ignore[attr-defined]
        handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())
        if redactor is not None:
            handler.addFilter(redactor)
        root.addHandler(handler)
    root.setLevel(level.upper())


def _redaction_filter() -> logging.Filter | None:
    try:
        import log_sanitizer

        return log_sanitizer.SecretAndPIIRedactingFilter()
    except Exception:  # the masking module is optional; losing it must not stop logging
        logging.getLogger(__name__).warning("günlük maskeleme filtresi yüklenemedi")
        return None
