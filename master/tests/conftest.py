"""Shared fixtures. Tests never call a real model or gateway, so they also run in CI."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

TEST_TOKEN = "test-agent-token"


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "workspaces")
    monkeypatch.setattr(config, "CNC_JOBS_DIR", tmp_path / "cnc_jobs")
    monkeypatch.setattr(config, "AGENT_TOKEN", TEST_TOKEN)


_REQUIRED_OPS09_MARKERS = frozenset({"unit", "contract", "integration", "e2e", "slow", "security"})


def pytest_collection_modifyitems(items):
    """OPS-09 / ALT-15: Reject any collected test lacking one of the 6 official pytest markers."""
    unmarked = [
        item.nodeid
        for item in items
        if not ({m.name for m in item.iter_markers()} & _REQUIRED_OPS09_MARKERS)
    ]
    if unmarked:
        sample = ", ".join(unmarked[:8])
        raise pytest.UsageError(
            f"OPS-09 ihlali: {len(unmarked)} testte resmi işaret (unit/contract/integration/e2e/slow/security) eksik: {sample}"
        )


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import app as app_module

    with TestClient(app_module.app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
