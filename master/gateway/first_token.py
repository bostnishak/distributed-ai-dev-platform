"""Time to first token of streamed answers, kept as a small rolling log."""

from __future__ import annotations

import json
from pathlib import Path

import config

_KEEP = 500


def _path() -> Path:
    return config.data_dir() / "first_token.jsonl"


def note(model: str, started: float, now: float) -> None:
    path = _path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-_KEEP:] if path.is_file() else []
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join([*lines, json.dumps({"model": model, "ms": int((now - started) * 1000)})]) + "\n", encoding="utf-8")
    except OSError:
        return  # a measurement must never disturb the answer


def medians() -> dict[str, int]:
    """Median milliseconds to the first token per model."""
    try:
        rows = [json.loads(line) for line in _path().read_text(encoding="utf-8").splitlines() if line.startswith("{")]
    except (OSError, ValueError):
        return {}
    grouped: dict[str, list[int]] = {}
    for row in rows:
        grouped.setdefault(row["model"], []).append(row["ms"])
    return {model: sorted(values)[len(values) // 2] for model, values in grouped.items()}
