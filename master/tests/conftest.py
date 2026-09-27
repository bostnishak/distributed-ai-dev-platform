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
    monkeypatch.setattr(config, "AGENT_TOKEN", TEST_TOKEN)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import app as app_module

    with TestClient(app_module.app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
