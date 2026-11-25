"""Pins/folders/sections are backed up per user and validated."""

import json

import pytest
from fastapi.testclient import TestClient

import app as master_app

pytestmark = pytest.mark.unit


def test_roundtrip_and_validation():
    c = TestClient(master_app.app)
    body = {"chat_meta": json.dumps({"a": {"pinned": True}}), "chat_folders": json.dumps(["Okul"])}
    assert c.put("/api/user/metatest/chat-meta", json=body).status_code == 200
    got = c.get("/api/user/metatest/chat-meta").json()
    assert json.loads(got["chat_meta"])["a"]["pinned"] is True and json.loads(got["chat_folders"]) == ["Okul"]
    assert c.put("/api/user/metatest/chat-meta", json={"chat_meta": "{not json"}).status_code == 422
    assert c.get("/api/user/../x/chat-meta").status_code in (400, 404)
