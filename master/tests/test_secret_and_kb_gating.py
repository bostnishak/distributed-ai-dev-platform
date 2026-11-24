"""Session secret has no repository-wide default; unrelated prompts do not pull engineering KB tables."""

import pytest

import company_rag
from auth import service

pytestmark = pytest.mark.unit


def test_signing_secret_is_random_per_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(service.config, "SECRET_KEY", "", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(service.config, "DATA_DIR", tmp_path, raising=False)
    monkeypatch.setattr(service, "_GENERATED_SECRET", None)
    first = service._signing_secret()
    import hashlib
    assert first != hashlib.sha256(b"dadp-local-dev-session-secret").digest()
    assert (tmp_path / ".session_secret").read_text().strip()
    monkeypatch.setattr(service, "_GENERATED_SECRET", None)
    assert service._signing_secret() == first  # persisted, stable across restarts


def test_explicit_secret_key_wins(monkeypatch):
    monkeypatch.setattr(service.config, "SECRET_KEY", "abc", raising=False)
    import hashlib
    assert service._signing_secret() == hashlib.sha256(b"abc").digest()


def test_poem_prompt_does_not_pull_iso_286_table():
    assert company_rag.search_company_kb_sync("Kısa bir şiir yaz ama 'güneş' kelimesi hiç geçmesin.") == []
    assert company_rag.search_company_kb_sync("H7 h6 mil delik toleransı nedir?")
