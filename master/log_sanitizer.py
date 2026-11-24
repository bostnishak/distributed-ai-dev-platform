"""SEC-23 & SEC-21: Structured Log & Telemetry Secret/PII Redaction Filter.

Masks tokens (`Authorization`, `X-Admin-Token`, `X-Agent-Key`, `Cookie`, `api_key`,
`tskey-...`, `sk-...`, `AIza...`, `ghp_...`, `agt_...`) and Turkish/standard PII
(TCKN, TR IBAN, phone numbers, email addresses) in all log records and audit payloads.
"""

from __future__ import annotations

import logging
import re
from typing import Any

_REDACT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # HTTP Auth headers & key-value secrets
    (re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer|basic)\s+)[^\s,;\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)((?:x-admin-token|x-agent-key|cookie|set-cookie|api_key|api-key|secret_key|agent_token|password)\s*[:=]\s*)[^\s,;\"']+"), r"\1[REDACTED]"),
    # Well-known secret prefixes
    (re.compile(r"\b(?:tskey-[A-Za-z0-9\-_]+|sk-[A-Za-z0-9\-_]{12,}|AIza[0-9A-Za-z\-_]{20,}|ghp_[0-9A-Za-z]{16,}|agt_[0-9a-fA-F]{16,})\b"), "[REDACTED_TOKEN]"),
    # Turkish IBAN (TR + 24 digits, optional spaces)
    (re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE), "[REDACTED_IBAN]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Turkish mobile phone numbers (+90 5xx / 05xx)
    (re.compile(r"(?<!\d)(?:\+90|0)\s*5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"), "[REDACTED_PHONE]"),
    # Turkish National ID (TCKN - 11 digits starting with 1-9)
    (re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)"), "[REDACTED_TCKN]"),
)

_SENSITIVE_KEYS = frozenset({
    "authorization",
    "x-admin-token",
    "x-agent-key",
    "cookie",
    "api_key",
    "secret_key",
    "password",
    "token",
    "agent_key",
    "agent_token",
    "prompt",
    "response",
})


def redact_sensitive_text(text: str) -> str:
    """Mask secrets, tokens, and PII patterns in arbitrary text."""
    out = (text or "")
    for pat, repl in _REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def redact_sensitive_data(obj: Any, debug_mode: bool = False) -> Any:
    """Recursively scrub secrets and PII from dicts/lists before logging or auditing."""
    if isinstance(obj, str):
        return redact_sensitive_text(obj)
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("prompt", "response"):
                if debug_mode and isinstance(v, str):
                    cleaned[k] = redact_sensitive_text(v)[:120] + ("..." if len(v) > 120 else "")
                else:
                    cleaned[k] = "[OMITTED]"
            elif kl in _SENSITIVE_KEYS or "secret" in kl or "password" in kl or "token" in kl:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_data(v, debug_mode=debug_mode)
        return cleaned
    if isinstance(obj, list):
        return [redact_sensitive_data(x, debug_mode=debug_mode) for x in obj]
    return obj


class SecretAndPIIRedactingFilter(logging.Filter):
    """Logging filter that scrubs secrets and PII from every emitted log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
            scrubbed = redact_sensitive_text(rendered)
            record.msg = scrubbed
            record.args = ()
        except (TypeError, ValueError, KeyError, AttributeError, RuntimeError) as _exc:
            logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
        return True


def install_log_redaction() -> None:
    """Attach SecretAndPIIRedactingFilter to root and uvicorn loggers idempotently."""
    flt = SecretAndPIIRedactingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, SecretAndPIIRedactingFilter) for f in logger.filters):
            logger.addFilter(flt)
        for handler in logger.handlers:
            if not any(isinstance(f, SecretAndPIIRedactingFilter) for f in handler.filters):
                handler.addFilter(flt)
