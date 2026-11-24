"""Centralized external prompt & text template loader for `master/prompts/` (PYD-01..35)."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@lru_cache(maxsize=256)
def load_prompt(name: str) -> str:
    """Load an external prompt/template file from `master/prompts/<name>` (UTF-8)."""
    target = (PROMPTS_DIR / name).resolve()
    if not str(target).startswith(str(PROMPTS_DIR.resolve())):
        raise ValueError(f"Invalid prompt path: {name}")
    return target.read_text(encoding="utf-8")


def render_prompt(name: str, **variables: object) -> str:
    """Load and format a prompt template using str.format(**variables)."""
    text = load_prompt(name)
    return text.format(**variables) if variables else text


def prompt_hash(name: str) -> str:
    """Return short SHA-256 content version hash for reproducibility tracking."""
    return hashlib.sha256(load_prompt(name).encode("utf-8")).hexdigest()[:12]
