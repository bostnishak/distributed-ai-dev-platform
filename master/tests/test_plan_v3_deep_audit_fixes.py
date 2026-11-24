"""Deep end-to-end verification tests for all 15 upgraded Plan v3 audit items (zero stubs/mocks)."""

from __future__ import annotations

import base64
import io
import math
import struct
import wave
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_test_wav_b64(rate: int = 8000, freq: float = 440.0, sec: float = 0.25) -> str:
    n = int(rate * sec)
    samples = [0] * 120 + [int(4000 * math.sin(2 * math.pi * freq * i / rate) + 500) for i in range(n)] + [0] * 120
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.mark.integration
def test_deep_audit_slide_icons_and_code_translate(client):
    """SUN-02 (24 SVG icons) & KOD-08 (AST multi-language translation + node syntax verification)."""
    icons = client.get("/api/productivity/slides/icons").json()
    assert icons["icon_count"] >= 24
    assert len(icons["icon_library"]) >= 24
    assert all("<svg" in svg for svg in icons["icon_library"].values())

    py_src = "def topla(a, b):\n    if a > 0:\n        print(a + b)\n    return a + b\n"
    js_res = client.post(
        "/api/productivity/code/translate",
        json={"code": py_src, "source_lang": "python", "target_lang": "javascript"},
    ).json()
    assert "function topla(a, b)" in js_res["translated_code"]
    assert "console.log" in js_res["translated_code"]
    assert js_res["syntax_verified"] is True

    go_res = client.post(
        "/api/productivity/code/translate",
        json={"code": py_src, "source_lang": "python", "target_lang": "go"},
    ).json()
    assert "func topla(" in go_res["translated_code"]
    assert "fmt.Println" in go_res["translated_code"]
    assert go_res["syntax_verified"] is True


@pytest.mark.integration
def test_deep_audit_audio_convert_and_video_generate(client):
    """MED-01 (real WAV/PCM cleaning/resampling) & MED-04 (real Pillow animated GIF slideshow)."""
    geo = client.post(
        "/api/productivity/media/geocode-distance",
        json={"lat1": 41.0082, "lon1": 28.9784, "lat2": 39.9334, "lon2": 32.8597},
    ).json()
    assert geo["audio_convert_available"] is True
    assert geo["video_generate_available"] is True

    wav_b64 = _make_test_wav_b64(rate=8000)
    aud = client.post(
        "/api/productivity/media/audio-convert",
        json={"wav_base64": wav_b64, "normalize": True, "trim_silence": True, "target_rate": 16000, "mono": True},
    )
    assert aud.status_code == 200
    ad = aud.json()
    assert ad["ok"] is True
    assert ad["output_rate"] == 16000
    assert base64.b64decode(ad["wav_base64"])[:4] == b"RIFF"

    vid = client.post(
        "/api/productivity/media/video-generate",
        json={
            "slides": [
                {"title": "Kare 1", "body": "DADP Sunumu"},
                {"title": "Kare 2", "body": "Yerel Video"},
            ],
            "width": 320,
            "height": 180,
            "frame_ms": 400,
        },
    )
    assert vid.status_code == 200
    vd = vid.json()
    assert vd["ok"] is True
    assert vd["frame_count"] == 2
    assert base64.b64decode(vd["media_base64"])[:6] in (b"GIF87a", b"GIF89a")


@pytest.mark.integration
def test_deep_audit_connectors_research_archive_and_rag(client, tmp_path, monkeypatch):
    """DOS-04 (Cloud Drive scan), DOS-05 (Git/GitHub repo inspect), ARS-01 & ARS-04 (SSRF-safe archive + RAG index)."""
    fake_drive = tmp_path / "sync_drive"
    fake_drive.mkdir()
    (fake_drive / "rapor.txt").write_text("Yerel senkron belgesi", encoding="utf-8")
    monkeypatch.setenv("CLOUD_DRIVE_ROOT", str(fake_drive))

    st = client.get("/api/productivity/connectors/status").json()
    assert st["cloud_drive"]["configured"] is True
    assert st["github_connector"]["configured"] is True

    scan = client.post("/api/productivity/connectors/cloud-drive/scan", json={"path": "", "limit": 10})
    assert scan.status_code == 200
    assert any(f["name"] == "rapor.txt" for f in scan.json()["files"])

    trav = client.post("/api/productivity/connectors/cloud-drive/scan", json={"path": "../../etc", "limit": 5})
    assert trav.status_code == 400

    gh = client.post("/api/productivity/connectors/github/inspect", json={"path": str(REPO_ROOT), "limit": 5})
    assert gh.status_code == 200
    assert gh.json()["ok"] is True
    assert gh.json()["commit_count"] >= 1

    ssrf = client.post(
        "/api/productivity/research/download-source",
        json={"url": "http://127.0.0.1:8000/secret", "content_text": "bad"},
    )
    assert ssrf.status_code == 400

    dl = client.post(
        "/api/productivity/research/download-source",
        json={
            "url": "https://docs.python.org/3/library/wave.html",
            "title": "Python Wave Modülü",
            "content_text": "Wave modülü PCM WAV ses dosyalarını okuma ve yazma için standart arayüz sağlar.",
        },
    )
    assert dl.status_code == 200
    assert dl.json()["indexed_doc_id"]
    ctx = client.get("/api/productivity/research/context?query=wave").json()
    assert ctx["archive_page_count"] >= 1


@pytest.mark.integration
def test_deep_audit_approval_gate_ha_remediate_and_custom_agent_chat(client):
    """AJN-06 (real approval blocking), OPR-02 (real remediate), OPR-04 (live HA status), AJN-01 & SOH-07."""
    # AJN-06: pending blocks with 409, rejected blocks with 403, approved executes cleanly
    gate = client.post("/api/productivity/agents/approvals", json={"action": "deploy_model", "payload": {"v": 2}}).json()
    gid = gate["id"]
    assert client.post(f"/api/productivity/agents/approvals/{gid}/execute").status_code == 409
    dec = client.post(
        f"/api/productivity/agents/approvals/{gid}/decide",
        json={"decision": "approved", "reviewer": "ishak", "note": "uygun"},
    )
    assert dec.status_code == 200 and dec.json()["status"] == "approved"
    ex = client.post(f"/api/productivity/agents/approvals/{gid}/execute")
    assert ex.status_code == 200 and ex.json()["gate"]["status"] == "executed"

    gate2 = client.post("/api/productivity/agents/approvals", json={"action": "drop_cache"}).json()
    client.post(f"/api/productivity/agents/approvals/{gate2['id']}/decide", json={"decision": "rejected"})
    assert client.post(f"/api/productivity/agents/approvals/{gate2['id']}/execute").status_code == 403

    # OPR-04: live HA leader reflected in /api/productivity/ops/logs
    client.post("/api/ha/lease", json={"node_id": "master-audit-1", "ttl_s": 30})
    logs = client.get("/api/productivity/ops/logs").json()
    assert logs["ha_master"]["leader_election"] is True
    assert logs["ha_master"]["leader"] == "master-audit-1"

    # OPR-02: real remediation execution
    rem = client.post(
        "/api/ux/health-wizard/remediate",
        json={"actions": ["ensure_dirs", "db_doctor", "init_dbs"]},
    )
    assert rem.status_code == 200
    assert rem.json()["ok"] is True
    assert len(rem.json()["results"]) == 3

    # AJN-01: custom agent profile resolution + system prompt injection
    import assistant_prep

    created = client.post(
        "/api/custom-agents",
        json={
            "user_id": "default",
            "name": "CNC Uzmanı",
            "instructions": "Her zaman ISO G-code güvenliğini önceliklendir.",
            "model_override": "qwen2.5-coder:7b",
            "allowed_tools": ["calculator"],
        },
    ).json()
    prof = assistant_prep.resolve_custom_agent_profile(created["agent_id"], "default")
    assert prof is not None
    assert "ISO G-code" in prof["instructions"]
    assert prof["model"] == "qwen2.5-coder:7b"

    msgs, _pre, _con, _src = assistant_prep.build_llm_stream_inputs(
        {
            "prompt": "Merhaba",
            "full_prompt": "Merhaba",
            "image_b64": None,
            "history": "[]",
            "user_id": "default",
            "conversation_id": "c_audit",
            "has_file": False,
            "is_prompt_conv": False,
            "custom_agent": prof,
        },
        "Temel sistem istemi",
        "",
    )
    assert "ISO G-code" in msgs[0]["content"]


@pytest.mark.unit
def test_deep_audit_frontend_voice_model_picker_high_contrast_and_extension():
    """SOH-06 (real voiceMode), SOH-07 (real modelPicker), high-contrast CSS, and EPK-34/ENT-03 sidepanel.js."""
    voice_js = (REPO_ROOT / "master" / "static" / "js" / "assistant_voice.js").read_text(encoding="utf-8")
    assert "toggleVoiceMode" in voice_js
    assert "speechSynthesis" in voice_js
    assert "voice-auto-submit" in voice_js

    enh_js = (REPO_ROOT / "master" / "static" / "js" / "chat_enhancements.js").read_text(encoding="utf-8")
    assert "modelPicker: getSelectedModel" in enh_js
    assert "voiceMode: toggleVoiceMode" in enh_js
    assert "customAgentPicker" in enh_js

    stream_js = (REPO_ROOT / "master" / "static" / "js" / "assistant_stream.js").read_text(encoding="utf-8")
    assert "formData.append('model'" in stream_js
    assert "formData.append('custom_agent_id'" in stream_js
    assert "assistant-reply-complete" in stream_js

    theme_css = (REPO_ROOT / "master" / "static" / "css" / "theme.css").read_text(encoding="utf-8")
    assert 'html[data-theme="high-contrast"]' in theme_css

    sp_html = (REPO_ROOT / "extensions" / "browser" / "sidepanel.html").read_text(encoding="utf-8")
    sp_js = (REPO_ROOT / "extensions" / "browser" / "sidepanel.js").read_text(encoding="utf-8")
    assert 'src="sidepanel.js"' in sp_html
    assert "consentEl.checked" in sp_js
    assert "chrome.runtime" in sp_js
