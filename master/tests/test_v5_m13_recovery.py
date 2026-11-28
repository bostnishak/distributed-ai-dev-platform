"""v5 milestone 13: snapshots and point-in-time restore, personal data scrubbing, learned rules and snippets."""

from __future__ import annotations

import asyncio
import json
import sqlite3

import pytest

import config
import failure_rules
import pii
import recovery
import training_pack

pytestmark = pytest.mark.unit


@pytest.fixture
def data(tmp_path, monkeypatch):
    root = tmp_path / "data"
    (root / "workspaces" / "p1").mkdir(parents=True)
    (root / "vendor").mkdir()
    (root / "vendor" / "buyuk.js").write_text("x" * 100, encoding="utf-8")
    (root / "workspaces" / "p1" / "index.html").write_text("<p>ilk</p>", encoding="utf-8")
    (root / "skills.json").write_text('[{"request": "a", "files": ["b"]}]', encoding="utf-8")
    with sqlite3.connect(root / "platform.db") as conn:
        conn.execute("CREATE TABLE notlar (metin TEXT)")
        conn.execute("INSERT INTO notlar VALUES ('bellek kaydı')")
    conn.close()
    monkeypatch.setattr(config, "DATA_DIR", root)
    monkeypatch.setattr(config, "DB_PATH", str(root / "platform.db"))
    monkeypatch.setattr(recovery, "_SETTINGS", tmp_path / "ai-os.config.json")
    (tmp_path / "ai-os.config.json").write_text('{"profil": "ilk"}', encoding="utf-8")
    return root


def _notes(root):
    conn = sqlite3.connect(root / "platform.db")
    try:
        return [row[0] for row in conn.execute("SELECT metin FROM notlar")]
    finally:
        conn.close()


def test_corrupted_data_is_brought_back_and_the_restore_can_be_undone(data):
    identifier = recovery.snapshot(password="deneme-parolası")
    assert [name for name, _size in recovery.available()] == [identifier]
    (data / "platform.db").write_bytes(b"bozuk" * 500)
    (data / "skills.json").unlink()
    (data / "workspaces" / "p1" / "index.html").write_text("silindi", encoding="utf-8")
    recovery._SETTINGS.write_text('{"profil": "bozuk"}', encoding="utf-8")
    report = recovery.restore(identifier, password="deneme-parolası")
    assert identifier in report and _notes(data) == ["bellek kaydı"]
    assert (data / "workspaces" / "p1" / "index.html").read_text(encoding="utf-8") == "<p>ilk</p>"
    assert json.loads((data / "skills.json").read_text(encoding="utf-8"))[0]["request"] == "a"
    assert json.loads(recovery._SETTINGS.read_text(encoding="utf-8")) == {"profil": "ilk"}
    assert (data / "backups" / f"onceki-{identifier}" / "platform.db").read_bytes().startswith(b"bozuk"), "bozuk durum da saklanır"


def test_snapshot_is_encrypted_skips_rebuildable_files_and_refuses_a_wrong_password(data):
    identifier = recovery.snapshot(password="doğru")
    raw = (recovery.folder() / f"backup-{identifier}.zip").read_bytes()
    assert b"bellek kayd" not in raw
    import pyzipper

    with pyzipper.AESZipFile(recovery.folder() / f"backup-{identifier}.zip") as archive:
        names = archive.namelist()
    assert not any("vendor/" in n and "workspaces" not in n for n in names) and any("workspaces/p1/index.html" in n for n in names)
    with pytest.raises(ValueError):
        recovery.restore(identifier, password="yanlış")
    with pytest.raises(ValueError):
        recovery.restore("../../etc", password="doğru")


def test_personal_data_is_removed_but_ordinary_numbers_stay():
    text = ("Ali: ali.veli@ornek.com, 0532 123 45 67, TC 10000000146, IBAN TR33 0006 1005 1978 6457 8413 26, "
            "kart 4111 1111 1111 1111, sunucu 192.168.1.20, yol C:\\Users\\ayse\\proje. Sipariş 12345678901, sürüm 127.0.0.1")
    cleaned = pii.scrub(text)
    for secret in ("ornek.com", "532 123", "10000000146", "6457", "4111", "192.168", "ayse"):
        assert secret not in cleaned, secret
    assert "12345678901" in cleaned and "127.0.0.1" in cleaned and "[KİMLİK-NO]" in cleaned and "C:\\Users\\[KULLANICI]\\proje" in cleaned


def test_training_pack_contains_no_personal_data(data):
    (data / "workspaces" / "p1" / "app.py").write_text("EPOSTA = 'ayse@ornek.com'\n", encoding="utf-8")
    (data / "trajectories.jsonl").write_text(json.dumps({"request": "ayse@ornek.com için sayfa", "workspace": "p1", "passed": True}) + "\n", encoding="utf-8")
    counts = training_pack.export(data / "paket")
    body = (data / "paket" / "sft_verified.jsonl").read_text(encoding="utf-8")
    assert counts["sft"] == 1 and "ornek.com" not in body and "[E-POSTA]" in body


def test_rules_are_general_and_offered_to_similar_requests_only(data):
    answers = iter(["Türkçe harf dönüşümünde str.lower yetmez; önce I ve İ harflerini ayrıca çevir.", "Beklenen sonuç 'ışık izmir' olmalı."])

    async def model(system, user):
        return next(answers)

    spec = "tr_lower(text): Türkçe küçük harfe çevir"
    rule = asyncio.run(failure_rules.mine(spec, "assert tr_lower('IŞIK') == 'ışık izmir'\nAssertionError", model))
    assert "str.lower" in rule
    assert asyncio.run(failure_rules.mine(spec, "assert x == 'ışık izmir'", model)) == "", "beklenen değeri yazan kural alınmaz"
    failure_rules.keep_snippet(spec, "def tr_lower(text):\n    return text.replace('I', 'ı').replace('İ', 'i').lower()\n")
    hint = failure_rules.hint("tr_title(text): Türkçe başlık biçimine çevir, küçük harf kurallarına uy")
    assert "str.lower" in hint and "def tr_lower" in hint
    assert failure_rules.hint("matris determinantı hesapla") == ""


def test_repaired_failure_becomes_a_rule(data):
    import workspace_smoke

    async def regenerate(rel, ask):
        assert rel == "kural" and "ZeroDivisionError" in ask
        return "Bölmeden önce bölenin sıfır olup olmadığını denetle."

    memory = workspace_smoke._RepairMemory(first_failure="Traceback\nZeroDivisionError: division by zero")
    asyncio.run(workspace_smoke._learn("ortalama hesaplayan uygulama yap", memory, regenerate))
    assert "sıfır" in failure_rules.hint("not ortalaması hesaplayan uygulama yap")
    asyncio.run(workspace_smoke._learn("x", workspace_smoke._RepairMemory(), regenerate))
