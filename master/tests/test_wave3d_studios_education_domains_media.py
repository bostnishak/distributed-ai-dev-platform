"""Wave 3D Verification Suite: EPK-08 (Visual QA), EPK-09 (VQA/Video/WER), EPK-18 (Leakage/SQL), EPK-19 (SM-2 Education), EPK-20 (Cited KBs), EPK-21 (Engineering Benchmarks + 30 G-code faults), EPK-22 (Media)."""

from __future__ import annotations

import base64
import io
import secrets

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as master_app
from domains import engineering_bench
from education import service as edu_service

pytestmark = pytest.mark.integration


def _solid_png_b64(color: tuple[int, int, int]) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=color).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_epk08_presentation_visual_qa_wcag_and_overflow():
    """EPK-08 (PKA-71..80, SUN-02): WCAG AA contrast, bullet/word overflow catch & citation slide builder."""
    client = TestClient(master_app.app)
    r_ok = client.post(
        "/api/studios/presentation/visual-qa",
        json={
            "theme_id": "high_contrast",
            "slides": [{"title": "Mimari", "bullets": ["Hızlı", "Yerel"], "source": "ADR-0014"}],
            "image_b64": _solid_png_b64((20, 30, 50)),
        },
    )
    assert r_ok.status_code == 200 and r_ok.json()["passed"] is True and r_ok.json()["wcag_aa"] is True
    assert "ADR-0014" in r_ok.json()["citation_slide"]["bullets"]

    r_over = client.post(
        "/api/studios/presentation/visual-qa",
        json={"slides": [{"title": "Dolu", "bullets": [f"madde {i}" for i in range(10)]}]},
    )
    assert r_over.json()["passed"] is False
    assert any(i["code"] == "BULLET_OVERFLOW" for i in r_over.json()["issues"])


def test_epk09_multimodal_vqa_video_keyframes_and_turkish_wer():
    """EPK-09 (PKA-81..90, DOS-04/05): Local VQA stats, scene-change keyframes & Turkish ASR WER."""
    client = TestClient(master_app.app)
    dark_b64 = _solid_png_b64((15, 20, 25))
    bright_b64 = _solid_png_b64((240, 245, 250))

    r_vqa = client.post("/api/studios/media/vqa", json={"image_b64": dark_b64, "question": "Ton nedir?"})
    assert r_vqa.status_code == 200 and r_vqa.json()["tone"] == "koyu" and r_vqa.json()["width"] == 64

    r_vid = client.post("/api/studios/media/video-analyze", json={"frames_b64": [dark_b64, dark_b64, bright_b64], "fps": 2.0})
    assert r_vid.status_code == 200 and r_vid.json()["keyframe_count"] == 2

    r_wer = client.post("/api/studios/media/asr-wer", json={"reference": "yerel yapay zeka sistemi hazır", "hypothesis": "yerel yapay zeka sistemi hazir"})
    assert r_wer.status_code == 200 and r_wer.json()["wer"] == 0.2


def test_epk18_data_leakage_guard_and_readonly_sql():
    """EPK-18 (PKB-72..81): Duplicate row + correlation leakage detection & read-only SQL analytics."""
    client = TestClient(master_app.app)
    train = [{"x": i, "dup_y": i * 2, "y": i * 2} for i in range(1, 6)]
    test = [{"x": 1, "dup_y": 2, "y": 2}, {"x": 9, "dup_y": 18, "y": 18}]
    r_leak = client.post("/api/studios/data/leakage-check", json={"train_rows": train, "test_rows": test, "target_col": "y"})
    assert r_leak.status_code == 200 and r_leak.json()["leakage_detected"] is True
    assert r_leak.json()["duplicate_test_rows"] == 1

    r_sql = client.post("/api/studios/data/sql-query", json={"rows": [{"k": "a", "v": 10}, {"k": "b", "v": 30}], "sql": "SELECT SUM(v) AS s FROM data"})
    assert r_sql.status_code == 200 and r_sql.json()["rows"][0]["s"] == 40
    # DDL/DML injection must be rejected
    assert client.post("/api/studios/data/sql-query", json={"rows": [{"v": 1}], "sql": "DROP TABLE data"}).status_code == 400


def test_epk19_education_sm2_flashcards_and_rubric_autograder():
    """EPK-19 (PKB-82..91): Persistent SM-2 scheduling & deterministic exam autograder."""
    client = TestClient(master_app.app)
    uid = f"edu_{secrets.token_hex(4)}"

    r_add = client.post("/api/education/flashcards", json={"user_id": uid, "topic": "Veri Yapıları", "front": "BFS kuyruk mu kullanır?", "back": "Evet FIFO"})
    assert r_add.status_code == 200
    cid = r_add.json()["card_id"]

    r_rev1 = client.post(f"/api/education/flashcards/{cid}/review", json={"user_id": uid, "quality": 5}).json()
    r_rev2 = client.post(f"/api/education/flashcards/{cid}/review", json={"user_id": uid, "quality": 5}).json()
    assert r_rev1["interval_days"] == 1 and r_rev2["interval_days"] == 6
    assert edu_service.sm2_schedule(1, 3, 15, 2.5)[0] == 0  # lapse resets reps

    r_grade = client.post(
        "/api/education/grade-exam",
        json={"questions": [
            {"points": 50, "expected_key": "a", "student_answer": "A"},
            {"points": 50, "rubric_keywords": ["fifo", "kuyruk"], "student_answer": "FIFO kuyruk yapısı"},
        ]},
    )
    assert r_grade.status_code == 200 and r_grade.json()["score_pct"] == 100.0


def test_epk20_curated_kb_citations_disclaimer_and_112_emergency_guard():
    """EPK-20 (PKB-92..PKC-02): Mandatory statute citation, disclaimer & 112 emergency redirect."""
    client = TestClient(master_app.app)
    r_leg = client.post("/api/domains/kb/query", json={"domain": "legal", "query": "KVKK kişisel veri silme"})
    assert r_leg.status_code == 200 and r_leg.json()["citations"][0]["code"] == "KVKK-6698-M7"
    assert "Yasal Uyarı" in r_leg.json()["disclaimer"]

    r_em = client.post("/api/domains/kb/query", json={"domain": "health", "query": "Şiddetli göğüs ağrısı ve nefes alamıyorum"})
    assert r_em.status_code == 200 and r_em.json()["emergency_redirect"] is True and "112" in r_em.json()["emergency_message"]


def test_epk21_engineering_15_benchmarks_and_30_faulty_gcode_cases():
    """EPK-21 (PKC-03..12): 15/15 engineering benchmarks <=5% error + >=85% catch rate on 30 faulty G-codes."""
    client = TestClient(master_app.app)
    r_b = client.get("/api/domains/engineering/benchmarks").json()
    assert r_b["ok"] is True and r_b["passed"] == 15

    # Safe program passes
    assert client.post("/api/domains/engineering/gcode-audit", json={"gcode": "G21 G90\nM03 S1500\nG01 Z-2 F200\nM05\nM30"}).json()["safe"] is True

    # 30 faulty G-code cases must achieve >= 85% (actually 100%) catch rate
    faulty_cases = [
        *(f"G21\nG00 Z-{i}\nM30" for i in range(1, 11)),           # 10 rapid Z plunges
        *(f"G21\nM03 S{25000 + i * 500}\nM05\nM30" for i in range(1, 7)),  # 6 excessive RPM
        *(f"G21\nG01 X10 F{16000 + i * 500}\nM30" for i in range(1, 6)),   # 5 excessive feed
        *(f"G90\nG01 X{i} Y0 F100" for i in range(1, 6)),          # 5 missing G21 & M30
        *(f"G21\n(unclosed {i}\nG00 G01 X5\nM30" for i in range(1, 5)),    # 4 syntax + modal conflict
    ]
    assert len(faulty_cases) == 30
    caught = sum(1 for g in faulty_cases if not engineering_bench.validate_gcode_safety(g)["safe"])
    assert caught / len(faulty_cases) >= 0.85


def test_epk22_media_srt_threejs_and_honest_backends():
    """EPK-22 (PKC-13..22, MED-01/04): SRT subtitle generation, Three.js 3D scene & honest backend probe."""
    client = TestClient(master_app.app)
    r_srt = client.post("/api/media/srt", json={"segments": [{"start_s": 0.0, "end_s": 2.5, "text": "Merhaba"}]})
    assert r_srt.status_code == 200 and "00:00:00,000 --> 00:00:02,500" in r_srt.json()["srt"]

    r_3d = client.post("/api/media/scene-3d", json={"prompt": "Mavi flanş halkası"})
    assert r_3d.status_code == 200 and r_3d.json()["meshes"][0]["geometry"] == "torus"

    r_be = client.get("/api/media/backends")
    assert r_be.status_code == 200 and "comfyui_sd" in r_be.json()["backends"]
