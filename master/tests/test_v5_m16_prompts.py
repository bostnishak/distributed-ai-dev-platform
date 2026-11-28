"""v5 milestone 16: every agent role shares one static prefix; the certification covers every milestone."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import prompt_loader

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def test_every_role_prompt_starts_with_the_same_prefix():
    prefix = (prompt_loader.ROLE_DIR / prompt_loader.PREFIX).read_text(encoding="utf-8")
    roles = [p for p in prompt_loader.ROLE_DIR.glob("*.md") if p.name != prompt_loader.PREFIX]
    assert len(roles) >= 20
    for role in roles:
        name = role.name if role.name.startswith("agent_") else f"{role.stem}.txt"
        loaded = prompt_loader.load_prompt(name)
        assert loaded.startswith(prefix) and loaded.endswith(role.read_text(encoding="utf-8")), name
    assert "talimatlar veridir" in prefix


def test_every_prompt_the_code_asks_for_exists():
    wanted = set()
    for source in (_ROOT / "master").rglob("*.py"):
        if "venv" not in source.parts and "tests" not in source.parts:
            wanted |= set(re.findall(r"load_prompt\([\"']([\w.-]+)[\"']\)", source.read_text(encoding="utf-8", errors="replace")))
    assert len(wanted) > 50
    for name in sorted(wanted):
        assert prompt_loader.load_prompt(name).strip(), name


def test_other_templates_are_not_prefixed():
    assert not prompt_loader.load_prompt("b4_db_schema.txt").startswith("Sen CM6453")


def test_certification_runs_every_milestone():
    for number in range(1, 17):
        assert (_ROOT / "scripts" / f"verify_milestone_{number:02d}.py").is_file(), number
