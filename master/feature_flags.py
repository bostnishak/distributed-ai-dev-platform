"""ai-os.config.json switches: which optional parts of the platform run.

  {"features": {"enable_web": false, "enable_nightly_eval": true}, "profiles": {"sessiz": {"enable_self_play": false}}}

A flag only sets the environment variable the feature already reads; a variable set by hand or in .env wins. `ai-os up
--profile sessiz` lays that profile's flags over the defaults.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)
CONFIG_FILE = Path(__file__).resolve().parent.parent / "ai-os.config.json"
# flag -> (variable, value when on, value when off)
FLAGS: dict[str, tuple[str, str, str]] = {
    "enable_web": ("WEB_GROUNDING", "1", "0"),
    "enable_code_run": ("CODE_RUN_ENABLED", "true", "false"),
    "enable_nightly_eval": ("SELF_EVAL_HOUR", "3", ""),
    "enable_self_play": ("SELF_PLAY_HOUR", "4", ""),
    "enable_scheduled_backup": ("BACKUP_INTERVAL_HOURS", "24", "0"),
    "enable_api_docs": ("ENABLE_DOCS", "1", "0"),
}


def read(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or CONFIG_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def chosen(profile: str = "", path: Path | None = None) -> dict[str, bool]:
    """The flags in force: the file's defaults with the named profile over them. ValueError for an unknown profile."""
    data = read(path)
    flags = dict(data.get("features") or {})
    if profile:
        profiles = data.get("profiles") or {}
        if profile not in profiles:
            raise ValueError(f"profil yok: {profile} (tanımlı: {', '.join(profiles) or 'hiç'})")
        flags.update(profiles[profile])
    for name in [n for n in flags if n not in FLAGS]:
        _log.warning("ai-os.config.json: bilinmeyen bayrak %s", name)
    return {name: bool(value) for name, value in flags.items() if name in FLAGS}


def apply(profile: str = "", path: Path | None = None, environ: dict | None = None) -> list[str]:
    """Set the variables the flags stand for; returns "name=on/off" lines for what was set."""
    target = os.environ if environ is None else environ
    applied = []
    for name, on in chosen(profile or target.get("AI_OS_PROFILE", ""), path).items():
        variable, yes, no = FLAGS[name]
        if variable not in target:
            target[variable] = yes if on else no
            applied.append(f"{name}={'açık' if on else 'kapalı'}")
    return applied
