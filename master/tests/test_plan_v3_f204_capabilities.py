"""Plan v3 Wave 6 behavioral verification tests for F204 capabilities (GUV/EGT/ALN/SOH/HAF/DOS/KOD/SUN/ARS/MED/VER/AJN/OPR/ENT)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as master_app
import config
import security_extensions as se
import security_middleware

pytestmark = pytest.mark.integration


@pytest.fixture()
def f204_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    security_middleware._API_RATE_LIMITER._state.clear()
    with TestClient(master_app.app) as c:
        yield c


@pytest.mark.security
def test_guv01_to_guv07_security_extensions(f204_client):
    # GUV-01: RFC 6238 TOTP setup + code verify
    setup = f204_client.post("/api/security/totp/setup?username=ishak").json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    code = se.totp_code(setup["secret"])
    assert f204_client.post("/api/security/totp/verify", json={"secret": setup["secret"], "code": code}).json()["valid"] is True
    assert f204_client.post("/api/security/totp/verify", json={"secret": setup["secret"], "code": "000000"}).json()["valid"] is False

    # GUV-02: Password strength
    weak = f204_client.post("/api/security/password-strength", json={"password": "password"}).json()
    strong = f204_client.post("/api/security/password-strength", json={"password": "Kuvvetli!Parola2026"}).json()
    assert weak["valid"] is False and strong["valid"] is True and strong["score"] >= 3

    # GUV-03 & GUV-04: Sessions + lockout
    assert "sessions" in f204_client.get("/api/security/sessions").json()
    assert f204_client.post("/api/security/sessions/revoke-all").json()["ok"] is True
    for _ in range(5):
        st = se.record_account_failure("locktest")
    assert st["locked"] is True and f204_client.get("/api/security/lockout/locktest").json()["locked"] is True

    # GUV-05, GUV-06, GUV-07: IP allowlist, secret scan, honest AV status
    assert f204_client.get("/api/security/ip-allowlist").json()["allowed_ips"]
    scan = f204_client.post("/api/security/secret-scan", json={"content": "AKIAIOSFODNN7EXAMPLE"}).json()
    assert scan["clean"] is False and scan["findings_count"] >= 1
    assert f204_client.get("/api/security/antivirus/status").json()["available"] is False


@pytest.mark.unit
def test_egt01_to_egt05_and_aln01_to_aln07_tools(f204_client):
    # Education studio
    q = f204_client.post("/api/tools/education/quiz", json={"topic": "Python", "count": 4}).json()
    assert len(q["questions"]) == 4
    lp = f204_client.post("/api/tools/education/lesson-plan", json={"topic": "Türev", "duration_minutes": 40}).json()
    assert sum(s["minutes"] for s in lp["curriculum_sections"]) == 40
    prog = f204_client.post("/api/tools/education/progress", json={"user_id": "u1", "topic": "Türev", "score_percent": 90}).json()
    assert prog["mastery"] == "ileri"
    grade = f204_client.post(
        "/api/tools/education/autograder",
        json={"code": "def add(a, b):\n    return a + b\n", "function_name": "add", "test_cases": [{"args": [2, 3], "expected": 5}]},
    ).json()
    from sandbox import runner

    if runner.docker_daemon_ready()[0]:
        assert grade["passed"] is True and grade["score"] == 100.0, grade
    else:
        assert grade["passed"] is False and "Docker" in grade["error"]
    assert len(f204_client.post("/api/tools/education/language-learning", json={}).json()["drills"]) >= 3

    # Domain calculators
    di = f204_client.post("/api/tools/domains/drug-interaction", json={"drugs": ["Warfarin", "Aspirin"]}).json()
    assert len(di["interactions"]) == 1 and "112" in di["disclaimer"]
    mats = f204_client.get("/api/tools/domains/materials?q=4140").json()
    assert mats["count"] == 1 and mats["materials"][0]["yield_mpa"] == 655
    metraj = f204_client.post("/api/tools/domains/metraj", json={"length_m": 10, "width_m": 5, "height_m": 0.2}).json()
    assert metraj["concrete_m3"] == 10.0 and metraj["rebar_kg"] == 1100.0
    circ = f204_client.post("/api/tools/domains/circuit", json={"voltage_v": 10, "r1_ohm": 100, "r2_ohm": 100}).json()
    assert circ["v_out_v"] == 5.0 and ".op" in circ["spice_netlist"]
    tax = f204_client.post("/api/tools/domains/turkey-tax", json={"annual_income_try": 200000}).json()
    assert tax["income_tax_try"] == round(158000 * 0.15 + 42000 * 0.20, 2)
    trip = f204_client.post("/api/tools/domains/trip-plan", json={"destination": "İzmir", "days": 3, "budget_try": 9000}).json()
    assert len(trip["itinerary"]) == 3 and trip["daily_budget_try"] == 3000.0
    nut = f204_client.post("/api/tools/domains/nutrition", json={"weight_kg": 75, "height_cm": 178, "age": 28, "sex": "male"}).json()
    assert nut["bmr_kcal"] > 1500 and nut["daily_kalori_kcal"] > nut["bmr_kcal"]


@pytest.mark.unit
def test_productivity_apis_code_data_media_agents_integrations(f204_client):
    # Chat archive, auto-title, project instructions, memory timeline, doc versions
    assert f204_client.post("/api/productivity/chats/c1/archive").json()["archived"] is True
    assert f204_client.post("/api/productivity/chats/auto-title", json={"text": "FastAPI ile güvenli REST API tasarımı"}).json()["auto_title"]
    assert f204_client.put("/api/productivity/projects/p1/instructions", json={"project_instructions": "Hep SI birim kullan."}).json()["project_instructions"] == "Hep SI birim kullan."
    assert "memory_timeline" in f204_client.get("/api/productivity/memory/timeline").json()
    assert len(f204_client.post("/api/productivity/documents/d1/versions", json={"text": "v1"}).json()["document_versions"]) == 1

    # Code tools
    rx = f204_client.post("/api/productivity/code/regex-tester", json={"pattern": r"\d+", "text": "a12 b34"}).json()
    assert rx["count"] == 2
    exp = f204_client.post("/api/productivity/code/explain", json={"text": "def f(x):\n    return x + 1\n"}).json()
    assert exp["valid"] is True and len(exp["line_by_line"]) == 2
    tr = f204_client.post("/api/productivity/code/translate", json={"code": "def f(x):\n    print(True)"}).json()
    assert "function f(x)" in tr["translated_code"] and "console.log(true)" in tr["translated_code"]
    assert len(f204_client.get("/api/productivity/code/templates").json()["template_gallery"]) == 8

    # Slides, mail merge, research, media QR & geocode
    assert "chart" in f204_client.get("/api/productivity/slides/icons").json()["icon_library"]
    assert f204_client.post("/api/productivity/slides/rehearse", json={"text": " ".join(["kelime"] * 130)}).json()["estimated_seconds"] == 60
    mm = f204_client.post("/api/productivity/documents/mail-merge", json={"template": "Sayın {{ad}}", "records": [{"ad": "Ayşe"}, {"ad": "Ali"}]}).json()
    assert mm["documents"] == ["Sayın Ayşe", "Sayın Ali"]
    assert f204_client.get("/api/productivity/research/context?query=kuantum").json()["today_iso"]
    assert "<svg" in f204_client.post("/api/productivity/media/qrcode", json={"text": "https://example.com"}).json()["qrcode_svg"]
    dist = f204_client.post("/api/productivity/media/geocode-distance", json={"lat1": 41.0082, "lon1": 28.9784, "lat2": 39.9334, "lon2": 32.8597}).json()
    assert 340 < dist["distance_km"] < 370  # Istanbul <-> Ankara ~350 km

    # Data studio: chart suggestion, cleaning, pivot, HTML dashboard, survey
    rows = [{"ay": "Ocak", "bolge": "Ege", "satis": 100}, {"ay": "Ocak", "bolge": "Ege", "satis": 100}, {"ay": "Şubat", "bolge": "Marmara", "satis": None}]
    assert f204_client.post("/api/productivity/data/suggest-chart", json={"rows": rows[:1]}).json()["suggest_chart"] == "bar"
    cleaned = f204_client.post("/api/productivity/data/clean", json={"rows": rows, "fill_value": 0}).json()
    assert cleaned["dedupe_rows_removed"] == 1 and cleaned["cleaned_rows"] == 2
    piv = f204_client.post("/api/productivity/data/pivot", json={"rows": cleaned["rows"], "row_key": "ay", "col_key": "bolge", "value_key": "satis"}).json()
    assert piv["pivot"]["Ocak"]["Ege"] == 100.0
    assert "<table" in f204_client.post("/api/productivity/data/dashboard-html", json={"rows": cleaned["rows"]}).json()["html"]
    assert f204_client.post("/api/productivity/data/surveys", json={"title": "Memnuniyet", "fields": [{"name": "puan"}]}).json()["id"]

    # Agents, ops, calendar .ics, social thread
    ca = f204_client.post("/api/productivity/agents/custom", json={"name": "Hukuk Asistanı", "instructions": "Atıflı yaz"}).json()
    assert ca["id"].startswith("asst_")
    assert f204_client.post("/api/productivity/agents/ag-1/drain?maintenance_mode=true").json()["maintenance_mode"] is True
    assert f204_client.post("/api/productivity/agents/schedule", json={"name": "Sabah Özeti", "prompt": "Özet"}).json()["enabled"] is True
    assert f204_client.post("/api/productivity/agents/approvals", json={"action": "deploy"}).json()["status"] == "pending"
    assert "usage_analytics" in f204_client.get("/api/productivity/ops/logs").json()
    ics = f204_client.post("/api/productivity/integrations/calendar.ics", json={"title": "Sprint Review", "start_iso": "2026-11-25T10:00:00Z", "end_iso": "2026-11-25T11:00:00Z"}).json()
    assert "BEGIN:VEVENT" in ics["ics"] and "SUMMARY:Sprint Review" in ics["ics"]
    soc = f204_client.post("/api/productivity/integrations/social-format", json={"text": " ".join(["duyuru"] * 60)}).json()
    assert len(soc["tweet_thread"]) >= 2

    # SQL-01..26 safe identifier builder, ENT-02 bot webhook, ENT-03 browser extension, KOD-01 offline editor
    import pathlib

    import sql_safe

    assert sql_safe.safe_ident("users") == '"users"'
    with pytest.raises(ValueError):
        sql_safe.safe_ident("users; DROP TABLE users;--")

    bot = f204_client.post("/api/productivity/integrations/bot-webhook?channel=telegram", json={"text": "Merhaba"}).json()
    assert bot["channel"] == "telegram" and "Merhaba" in bot["reply"]

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    assert (repo_root / "extensions" / "browser" / "manifest.json").is_file()
    assert (repo_root / "master" / "static" / "vendor" / "code_editor.js").is_file()
