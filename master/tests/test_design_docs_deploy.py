"""OKLCH design system, version-pinned library notes and hardened deployment files."""

import pytest

import deploy_kit
import design_system
import docs_vault

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("request_text", ["fintech paneli tasarla", "bir kafe sitesi", "portfolyo sitesi", "klinik randevu paneli", "x web sayfası"])
def test_generated_palettes_are_readable(request_text, dark):
    colours = design_system.palette(request_text, dark)
    for background in ("--bg", "--surface"):
        assert design_system.contrast(colours["--text"], colours[background]) >= 7
        assert design_system.contrast(colours["--text-muted"], colours[background]) >= 4.5
    assert design_system.contrast(colours["--on-accent"], colours["--accent"]) >= 4.5


def test_users_colours_are_never_overridden():
    assert design_system.brief("şık bir panel tasarla")
    assert design_system.brief("şık bir panel, ana renk #ff0000") == ""
    assert design_system.brief("mavi bir site") == ""
    assert design_system.brief("toplama fonksiyonu yaz") == ""
    assert design_system.oklch_to_hex(1.0, 0.0, 0) == "#ffffff" and design_system.oklch_to_hex(0.0, 0.0, 0) == "#000000"


def test_library_version_is_cached_and_reused_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(docs_vault, "_vault", lambda: tmp_path)
    calls = []

    def fetch(registry, name):
        calls.append(name)
        return {"info": {"version": "9.9.1", "summary": "web framework"}}

    assert "fastapi 9.9.1" in docs_vault.brief("FastAPI ile bir api yaz", fetch)
    docs_vault.brief("fastapi api", fetch)
    assert calls == ["fastapi"]

    def offline(registry, name):
        raise OSError("ağ yok")

    old = docs_vault.lookup("pypi", "fastapi", offline, now=10**10)
    assert old["stale"] and old["version"] == "9.9.1"
    assert docs_vault.lookup("pypi", "flask", offline) is None and docs_vault.brief("flask uygulaması", offline) == ""


def test_dockerfile_is_written_only_when_asked_and_passes_its_own_lint(tmp_path):
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\n\napp = FastAPI()\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    assert deploy_kit.apply(tmp_path, "bir api yaz") == ""
    assert "eklendi" in deploy_kit.apply(tmp_path, "bir api yaz ve docker ile yayına al")
    text = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert deploy_kit.lint(text) == [] and 'uvicorn main:app --host 0.0.0.0' in text and "uvicorn" in (tmp_path / "requirements.txt").read_text(encoding="utf-8")


def test_lint_names_the_usual_mistakes():
    found = deploy_kit.lint("FROM python\nENV API_KEY=abc123\nADD https://x.example/a.sh /a.sh\nCMD python a.py\n")
    assert len(found) == 5


@pytest.mark.parametrize("prompt", ['"elma armut kiraz elma" metninde kaç kelime var?', "elma armut kiraz elma metninde kaç kelime var?"])
def test_word_count_ignores_the_question_words(prompt):
    import text_tools

    assert "**4**" in text_tools.answer(prompt)
