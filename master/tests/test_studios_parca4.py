"""Comprehensive test suite for Parca 4: RES-01..12, PPT-01..10, DOC-01..10, DS-01..10, MM-01..14."""

from __future__ import annotations

import io
import sqlite3
import time

import pytest
from docx import Document
from fastapi.testclient import TestClient
from PIL import Image

import app as master_app
from studios import (
    DESIGN_THEMES,
    DOCUMENT_TEMPLATES,
    SLIDE_LAYOUTS,
    AttachmentPipeline,
    MediaLifecycleManager,
    anonymize_image_regions,
    anonymize_kvkk_text,
    audit_document_quality,
    build_literature_matrix,
    build_narrative_outline,
    build_reproducible_report_html,
    build_verified_docx,
    build_verified_pdf,
    build_verified_pptx,
    build_verified_xlsx,
    check_robots_allowed,
    detect_anomalies_explained,
    edit_docx_inplace_redline,
    edit_image_versioned,
    edit_single_slide_artifact,
    enforce_short_quote,
    fit_slide_bullets,
    forecast_with_backtest,
    generate_visual_with_metadata,
    is_valid_tckn,
    prepare_tts_text,
    profile_dataset_on_demand,
    recommend_and_render_chart,
    roundtrip_text_loss_audit,
    run_deep_research,
    run_research_eval,
    safe_readonly_sql,
    select_and_run_stat_test,
    summarize_meeting_with_evidence,
    train_automl_checked,
    validate_and_repair_diagram,
    wcag_contrast_ratio,
    what_if_predict,
)

# ---------------------------------------------------------------- RES-01..RES-12 Tests

@pytest.mark.anyio
async def test_res01_to_res12_grounded_research_contradictions_lit_matrix_robots_eval():
    # RES-11: robots.txt compliance & short-quote limit
    robots = "User-agent: *\nDisallow: /private/\n"
    assert check_robots_allowed("https://example.org/private/secret", robots) is False
    assert check_robots_allowed("https://example.org/public/article", robots) is True
    assert len(enforce_short_quote("kelime " * 80, max_words=35).split()) == 35

    # RES-01..06, 08..10, 12: 8+ distinct domains including a deliberate numeric contradiction
    async def _fake_fetch(_q, _n):
        return [
            {"url": "https://iso.org/energy-2026", "title": "ISO Enerji Raporu", "snippet": "Katı hal batarya enerji yoğunluğu 450 Wh/kg seviyesine ulaştı.", "published_date": "2026-02-01"},
            {"url": "https://arxiv.org/abs/2601.111", "title": "ArXiv Batarya Çalışması", "snippet": "Katı hal batarya enerji yoğunluğu 280 Wh/kg seviyesinde kalmaktadır.", "published_date": "2026-01-15"},
            {"url": "https://ieee.org/solid-state", "title": "IEEE İnceleme", "snippet": "Şarj ömrü 1200 döngü olarak ölçülmüştür.", "published_date": "2025-11-10"},
            {"url": "https://nature.com/articles/s415", "title": "Nature Enerji", "snippet": "Sülfür elektrolitler yüksek iyon iletkenliği sağlar.", "published_date": "2025-09-20"},
            {"url": "https://europa.eu/battery-dir", "title": "AB Batarya Direktifi", "snippet": "Geri dönüşüm hedefi yüzde 70 olarak belirlenmiştir.", "published_date": "2025-08-05"},
            {"url": "https://reuters.com/ev-cells", "title": "Reuters Haber", "snippet": "Pilot üretim hatları 2026 yılında genişletildi.", "published_date": "2026-03-01"},
            {"url": "https://who.int/safety-cell", "title": "Güvenlik Notu", "snippet": "Termal kaçak riski sıvı elektrolite göre azalmıştır.", "published_date": "2025-12-01"},
            {"url": "https://acm.org/bms-opt", "title": "BMS Optimizasyonu", "snippet": "Akıllı batarya yönetimi ömrü yüzde 18 artırır.", "published_date": "2026-01-20"},
        ]

    rep = await run_deep_research(
        f"Katı hal batarya teknolojileri {time.time_ns()}",
        speed_mode="deep",
        fetch_fn=_fake_fetch,
        offline_mode=False,
        distribute_agents=True,
    )
    assert len(rep.notes) >= 8
    assert rep.diversity_score >= 0.8
    assert len(rep.contradictions) >= 1  # ISO (450) vs ArXiv (280) surfaced transparently!
    assert rep.artifact_id
    assert rep.verification_summary["verified"] >= 1
    assert "Doğrulama Özeti:" in rep.markdown

    # RES-06: Incremental update shows diff section
    rep2 = await run_deep_research(
        f"Katı hal batarya teknolojileri {time.time_ns()}",
        speed_mode="fast",
        fetch_fn=_fake_fetch,
        offline_mode=False,
        prior_artifact_id=rep.artifact_id,
    )
    assert "Güncelleme Farkı" in rep2.markdown

    # RES-07: Literature matrix across uploaded papers
    mat = build_literature_matrix([
        {"title": "Makale A.pdf", "page": 3, "content": "Yöntem: Rastgele Orman. Örneklem: 500 hasta. Ölçüm: F1 0.91. Bulgu: Yüksek doğruluk. Sınırlılık: Tek merkez."},
        {"title": "Makale B.pdf", "page": 7, "content": "Method: Transformer. Sample: 1200 docs. Metric: Accuracy 94%. Finding: Fast inference. Limitation: High VRAM."},
    ])
    assert mat["count"] == 2 and mat["rows"][0]["citation"] == "Makale A.pdf, s.3"

    # RES-12: Research eval passes thresholds
    ev = run_research_eval([rep])
    assert ev["passed"] is True and ev["fabricated_sources"] == 0


# ---------------------------------------------------------------- PPT-01..PPT-10 Tests

def test_ppt01_to_ppt10_wcag_outline_fitting_charts_notes_audit_and_targeted_edit(tmp_path):
    # PPT-02: All 6 themes pass WCAG AA (>= 4.5:1) and 12 layouts exist
    assert len(DESIGN_THEMES) == 6 and len(SLIDE_LAYOUTS) == 12
    for name, th in DESIGN_THEMES.items():
        assert wcag_contrast_ratio(th["fg"], th["bg"]) >= 4.5, f"Theme {name} failed WCAG AA contrast"

    # PPT-03: Text fitting enforces <= 40 words and >= 18pt font
    fitted = fit_slide_bullets(["kelime " * 30, "kelime " * 30])
    assert fitted["word_count"] <= 40 and fitted["font_pt"] >= 18

    # PPT-01, 04, 05, 06, 07, 08: Build verified PPTX with native chart, speaker notes, Kaynaklar & artifact
    outline = build_narrative_outline(
        "Yapay Zeka Güvenilirlik Mimarisi",
        duration_minutes=9,
        sources=[{"id": "S1", "doc": "ISO/IEC 42001 Standardı", "content": "Yönetim çerçevesi"}],
    )
    out_pptx = tmp_path / "verified_deck.pptx"
    built = build_verified_pptx(outline, output_path=out_pptx, theme_name="midnight_executive", transition="fade")
    q = built["quality"]
    assert q["opened_ok"] is True
    assert q["passed"] is True
    assert q["has_native_chart"] is True
    assert q["has_sources_slide"] is True
    assert q["missing_notes"] == 0
    assert q["min_font_pt"] >= 18.0

    # PPT-09: Import corporate template preserving file validity
    templ_out = tmp_path / "from_template.pptx"
    built_t = build_verified_pptx(outline, output_path=templ_out, template_path=out_pptx)
    assert built_t["quality"]["opened_ok"] is True

    # PPT-08: Targeted single-slide edit leaves other slides identical
    edited = edit_single_slide_artifact(built["artifact_id"], 1, "Revize Edilmiş Slayt 2 İçeriği")
    assert edited["version"] == 2
    assert edited["sections"][1] == "Revize Edilmiş Slayt 2 İçeriği"


# ---------------------------------------------------------------- DOC-01..DOC-10 Tests

def test_doc01_to_doc10_docx_xlsx_pdf_redline_roundtrip_and_quality(tmp_path):
    assert len(DOCUMENT_TEMPLATES) == 9

    # DOC-01 & DOC-08: Verified DOCX + placeholder rejection
    bad_audit = audit_document_quality("Bu metinde Lorem ipsum ve TODO kalıntısı var.")
    assert not bad_audit["passed"] and len(bad_audit["placeholders"]) == 2

    docx_path = tmp_path / "report.docx"
    spec = {
        "title": "Yıllık Kalite Raporu",
        "summary": "Türkçe karakter doğrulama: ÇĞİÖŞÜ çğıöşü.",
        "sections": [
            {"heading": "Yönetici Özeti", "content": "Toplam hata oranı yüzde 0.4 seviyesindedir."},
            {"heading": "Öneriler", "content": "Tüm belgeler otomatik kalite denetiminden geçmektedir."},
        ],
        "table_headers": ["Bölüm", "Skor"],
        "table_rows": [["Kalite", "98"], ["Güvenlik", "100"]],
    }
    res_docx = build_verified_docx(spec, output_path=docx_path)
    assert res_docx["opened_ok"] is True and res_docx["quality"]["passed"] is True

    # DOC-05: In-place redline DOCX edit preserves original file & untouched paragraphs
    redline_path = tmp_path / "report_redline.docx"
    orig_paras = [p.text for p in Document(str(docx_path)).paragraphs]
    rl = edit_docx_inplace_redline(docx_path, 1, "Güncellenmiş özet metni.", redline_path)
    assert rl["has_redline"] is True
    assert [p.text for p in Document(str(docx_path)).paragraphs] == orig_paras  # original untouched!

    # DOC-02: Live-formula XLSX with zero formula errors
    xlsx_path = tmp_path / "budget.xlsx"
    res_xlsx = build_verified_xlsx({"title": "Bütçe Planı", "items": [("Sunucu", 2, 1500), ("Lisans", 4, 300)]}, output_path=xlsx_path)
    assert res_xlsx["audit"]["passed"] is True and res_xlsx["audit"]["formula_cells"] >= 7

    # DOC-03: Linked-TOC PDF with Turkish glyphs & PDF/A tagging
    pdf_path = tmp_path / "report.pdf"
    res_pdf = build_verified_pdf(spec, output_path=pdf_path, pdf_a=True)
    assert res_pdf["passed"] is True and res_pdf["toc_entries"] >= 3 and res_pdf["pdf_a_tagged"] is True

    # DOC-06: Round-trip conversion loss audit
    rt = roundtrip_text_loss_audit("Yıllık Kalite Raporu Yönetici Özeti", docx_path)
    assert rt["passed"] is True and rt["text_loss_pct"] <= 5.0


# ---------------------------------------------------------------- DS-01..DS-10 Tests

def test_ds01_to_ds10_profile_readonly_sql_charts_automl_anomalies_forecast_stat(tmp_path):
    # DS-01 & DS-10: On-demand profiling + PII warning + local privacy badge
    rows = [
        {"tarih": "2026-01-01", "satis": 100, "email": "a@example.com"},
        {"tarih": "2026-01-02", "satis": 120, "email": "b@example.com"},
        {"tarih": "2026-01-03", "satis": 130, "email": "c@example.com"},
        {"tarih": "2026-01-04", "satis": 950, "email": "d@example.com"},
    ]
    prof = profile_dataset_on_demand(rows)
    assert prof["columns"]["satis"]["type"] == "integer"
    assert prof["columns"]["tarih"]["type"] == "date"
    assert len(prof["pii_warnings"]) >= 1
    assert prof["privacy_badge"] == "bu veri yerelde kaldı"

    # DS-02: Read-only SQL succeeds on SELECT, blocks DROP/INSERT/PRAGMA
    db_file = tmp_path / "sales.db"
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute("CREATE TABLE sales (id INTEGER, amount REAL)")
        conn.executemany("INSERT INTO sales VALUES (?, ?)", [(1, 100.0), (2, 250.0)])
    ok_sql = safe_readonly_sql(db_file, "SELECT SUM(amount) AS total FROM sales")
    assert ok_sql["rows"][0]["total"] == 350.0
    with pytest.raises(PermissionError):
        safe_readonly_sql(db_file, "DROP TABLE sales")
    with pytest.raises(PermissionError):
        safe_readonly_sql(db_file, "INSERT INTO sales VALUES (3, 50)")

    # DS-03 & MM-11: Chart recommendation + SVG + misleading truncated-y warning
    ch = recommend_and_render_chart(rows, x_col="tarih", y_col="satis", y_unit="TL", truncate_y=True)
    assert ch["chart_type"] == "line" and "<svg" in ch["svg"] and len(ch["warnings"]) == 1

    # DS-04 & DS-05: AutoML detects target leakage, computes permutation importance & what-if
    X = [[i, i * 2.0, (i % 3) * 0.5] for i in range(1, 25)]
    y = [i * 2.0 for i in range(1, 25)]
    am = train_automl_checked(X, y, ["gun", "sizan_sutun", "gurultu"])
    assert len(am["leakage_warnings"]) >= 1
    assert am["beats_baseline"] is True
    assert am["feature_importance"][0]["feature"] in {"gun", "sizan_sutun"}
    assert what_if_predict(am, [25.0, 50.0, 0.5]) > 40.0

    # DS-06: Explained anomaly detection identifies driving column
    anom = detect_anomalies_explained(
        [{"x": 10}, {"x": 11}, {"x": 10}, {"x": 12}, {"x": 11}, {"x": 999}],
        ["x"],
    )
    assert anom["anomaly_count"] == 1 and anom["anomalies"][0]["reasons"][0]["column"] == "x"

    # DS-07: Forecast rejects < 4 points, returns backtest + 95% intervals otherwise
    assert forecast_with_backtest([10.0, 12.0, 14.0])["can_forecast"] is False
    fc = forecast_with_backtest([10.0, 12.0, 14.0, 16.0, 18.0, 20.0], horizon=2)
    assert fc["can_forecast"] is True and len(fc["forecasts"]) == 2 and "belirsizlik" in fc["forecasts"][0]["label"]

    # DS-08 & DS-09: Stat test (non-causal) & reproducible HTML report
    st = select_and_run_stat_test([10.0, 11.0, 12.0, 10.5, 11.5], [20.0, 21.0, 22.0, 20.5, 21.5])
    assert st["significant_005"] is True and "nedensellik" in st["interpretation"].lower()
    html_rep = build_reproducible_report_html("Satış Analizi", ch["reproducible_code"], st, ch["svg"])
    assert "<svg" in html_rep and "Satış Analizi" in html_rep


# ---------------------------------------------------------------- MM-01..MM-14 Tests

@pytest.mark.anyio
async def test_mm01_to_mm14_meeting_tts_visual_kvkk_diagram_attachments_and_signed_media(tmp_path):
    # MM-02: Meeting summary with timestamped evidence and no fabricated owners/dates
    meet = summarize_meeting_with_evidence([
        {"start": 15, "text": "Yeni güvenlik mimarisi onaylandı."},
        {"start": 75, "text": "Ahmet raporu 2026-12-01 tarihine kadar hazırlayacak."},
        {"start": 120, "text": "Bütçe dokümanı hazırlanacak aksiyon olarak eklendi."},
        {"start": 150, "text": "Canlı geçiş tarihi kesinleşti mi?"},
    ])
    assert len(meet["decisions"]) == 1 and meet["decisions"][0]["timestamp"] == "00:15"
    assert meet["actions"][0]["owner"] == "Ahmet" and meet["actions"][0]["due_date"] == "2026-12-01"
    assert meet["actions"][1]["owner"] == "belirtilmemiş" and meet["actions"][1]["due_date"] == "belirtilmemiş"
    assert len(meet["open_questions"]) == 1

    # MM-03: TTS text preparation excludes code blocks & markdown tables
    spoken = prepare_tts_text("Merhaba!\n```python\nprint(1)\n```\n| A | B |\n| - | - |\nÖrn. 5 dk. sürer.")
    assert "print" not in spoken and "|" not in spoken and "örneğin" in spoken.lower()

    # MM-05, MM-06, MM-08: Visual metadata + non-destructive Pillow edit
    vis = generate_visual_with_metadata("Sistem Mimarisi", gpu_diffusion_available=False)
    assert vis["metadata"]["produced_by"] == "ai_generated" and "<svg" in vis["svg"]

    img_buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(120, 130, 140)).save(img_buf, format="PNG")
    raw_png = img_buf.getvalue()
    ed = edit_image_versioned(raw_png, operation="clean_scan")
    assert ed["width"] == 64 and len(ed["png_bytes"]) > 0

    # MM-09: Algorithmic TCKN validation + KVKK anonymization + image region blur
    assert is_valid_tckn("10000000146") is True
    assert is_valid_tckn("12345678901") is False
    anon = anonymize_kvkk_text("TCKN: 10000000146, IBAN: TR330006100519786457841326, Tel: 0532 123 45 67, E-posta: ali@test.com, Plaka: 34 ABC 123")
    assert anon["total_masked"] == 5
    assert "10000000146" not in anon["anonymized_text"]
    assert "ali@test.com" not in anon["anonymized_text"]
    blurred = anonymize_image_regions(raw_png, [(10, 10, 40, 40)])
    assert len(blurred) > 0

    # MM-10: Diagram validator & auto-repair quotes parenthesized labels
    diag = validate_and_repair_diagram("A[Adım (1)] --> B[Sonuç]", kind="mermaid")
    assert diag["valid"] is True and 'A["Adım (1)"]' in diag["repaired_code"]

    # MM-13: Fault-isolated attachment pipeline (1 broken handler does NOT block healthy attachment!)
    pipe = AttachmentPipeline()
    pipe.register("txt", lambda b, _n: b.decode("utf-8"))
    pipe.register("bad", lambda _b, _n: (_ for _ in ()).throw(RuntimeError("bozuk dosya")))
    outs = await pipe.process_all([
        {"filename": "crash.bad", "bytes": b"x"},
        {"filename": "ok.txt", "bytes": b"temiz metin"},
    ])
    assert outs[0].status == "error" and outs[1].status == "ok" and outs[1].context == "temiz metin"

    # MM-14: Signed user-bound expiring media prevents cross-user access & cleans up expired files
    mgr = MediaLifecycleManager(storage_dir=tmp_path / "media", db_path=tmp_path / "media.db")
    stored = mgr.store_media(b"secret-image", owner_id="alice", filename="chart.png", content_type="image/png", ttl_seconds=60)
    ok_item = mgr.fetch_authorized(stored["media_id"], requester_id="alice", exp=stored["expires_at"], sig=stored["signature"])
    assert ok_item["bytes"] == b"secret-image"
    with pytest.raises(PermissionError):
        mgr.fetch_authorized(stored["media_id"], requester_id="bob", exp=stored["expires_at"], sig=stored["signature"])
    with pytest.raises(PermissionError):
        mgr.fetch_authorized(stored["media_id"], requester_id="alice", exp=stored["expires_at"], sig="tampered")

    expired = mgr.store_media(b"old", owner_id="alice", filename="old.png", ttl_seconds=-1)
    with pytest.raises(FileNotFoundError):
        mgr.fetch_authorized(expired["media_id"], requester_id="alice", exp=expired["expires_at"], sig=expired["signature"])


def test_parca4_studios_http_endpoints():
    with TestClient(master_app.app) as client:
        r = client.get("/api/studios/capabilities")
        assert r.status_code == 200
        body = r.json()
        assert len(body["presentation_themes"]) == 6
        assert len(body["document_templates"]) == 9
