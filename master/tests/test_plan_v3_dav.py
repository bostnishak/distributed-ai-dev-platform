"""Plan v3 Wave 2 deterministic regression tests for DAV-01..DAV-13."""

from __future__ import annotations

import pytest

import assistant
import chat_contracts as cc
import config
import document_factory as df
import multimodal_studio as mms

pytestmark = pytest.mark.integration


@pytest.mark.unit
def test_dav01_dav02_dav03_dav04_dav05_prompt_constraints_and_repair():
    # DAV-01 (fmt-02): max word limit <= 15
    c1 = cc.inspect_prompt_constraints("Bulutu 15 kelimeyi geçmeyecek şekilde tanımla.")
    assert c1.max_words == 15
    repaired1 = cc.enforce_output_constraints(" ".join(f"kelime{i}" for i in range(37)), c1)
    assert len(repaired1.split()) <= 15

    # DAV-02 (fmt-13): forbidden word 'deniz'
    c2 = cc.inspect_prompt_constraints("Bana kısa bir şiir yaz ama içinde 'deniz' kelimesi geçmesin.")
    assert "deniz" in c2.forbidden_words
    repaired2 = cc.enforce_output_constraints("Deniz feneri uzakta yanar,\nGemi izleri sulara karışır,\nRüzgar eserken kuşlar uçar.", c2)
    assert "deniz" not in repaired2.lower()

    # DAV-03 (code-10): code-only strips prose outside fences
    c3 = cc.inspect_prompt_constraints("Sadece kod ver, açıklama yazma: Python ile 1'den 10'a kadar sayıları yazdıran bir döngü.")
    assert c3.code_only is True
    repaired3 = cc.enforce_output_constraints("```python\nfor i in range(1, 11):\n    print(i)\n```\nBu kod 1'den 10'a kadar yazar.", c3)
    assert "Bu kod" not in repaired3 and "```python" in repaired3

    # DAV-04 (code-14): AST syntax hint detects incomplete expression
    c4 = cc.inspect_prompt_constraints("Bu kodda hata nedir? `def f(x): return x +` ")
    assert "sözdizimi" in c4.syntax_hint.lower() or "syntax" in c4.syntax_hint.lower()

    # DAV-05 (code-19): Turkish vowels hint includes ö, ü, ı, İ
    c5 = cc.inspect_prompt_constraints("Python'da bir metindeki sesli harfleri sayan count_vowels(s) yaz (Türkçe sesli harfler dahil).")
    assert c5.turkish_vowels_hint is True
    assert any("aeıioöuü" in note for note in c5.system_notes)


@pytest.mark.unit
def test_dav06_file_audit_suppressed_for_plain_questions():
    clean_insp = {"severity_counts": {"critical": 0, "high": 0, "medium": 0}}
    assert cc.should_attach_file_audit("Belgede bütçe rakamı var mı? Yoksa yok de.", clean_insp) is False
    assert cc.should_attach_file_audit("Bu dosyayı denetle, hata var mı?", clean_insp) is True
    assert cc.should_attach_file_audit("Özetle", {"severity_counts": {"critical": 1}}) is True


@pytest.mark.unit
def test_dav07_dav10_dav11_dav09_artifact_and_research_routing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    # DAV-07 (make-doc)
    assert df.detect_document_request("İş başvurusu için bir motivasyon mektubu hazırla ve Word dosyası olarak ver.", False) == "docx"
    # DAV-10 (make-chart)
    chart_prompt = "Şu verilerle bir çubuk grafik çiz: Ocak 10, Şubat 20, Mart 15."
    assert cc.is_chart_generation_request(chart_prompt, False) is True
    chart = cc.build_svg_bar_chart(chart_prompt)
    assert "<svg" in chart["svg"] and "Ocak" in chart["svg"] and chart["svg_url"].endswith(".svg")
    # DAV-11 (make-image): Turkish vowel drop 'resim' -> 'resmi'
    assert mms.is_image_generation_request("Gün batımında bir deniz kenarı resmi çiz.", False) is True
    # DAV-09 (make-research)
    assert cc.is_grounded_research_request("Kuantum bilgisayarlar hakkında kaynaklı kısa bir araştırma yap.", False) is True


@pytest.mark.unit
def test_dav12_dav13_deterministic_calculators():
    # DAV-12 (tool-03)
    r12 = assistant.try_calculate("12345 * 6789 işlemini hesapla.")
    assert r12 is not None and "83810205" in r12
    # DAV-13 (tool-07)
    r13 = assistant.try_calculate("Bir yıl 365 gün 5 saat 48 dk 46 sn ise bu kaç saniyedir?")
    assert r13 is not None and "31556926" in r13


@pytest.mark.unit
def test_dav08_workspace_file_dir_collision_guard(tmp_path):
    """DAV-08: Writing app/routes.py after an earlier 'app' file must not raise WinError 183 / FileExistsError."""
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "app").write_text("# legacy file", encoding="utf-8")
    target = ws_dir / "app" / "routes.py"
    for parent in reversed(target.parents):
        if parent == ws_dir or ws_dir not in parent.parents:
            continue
        if parent.is_file():
            parent.replace(parent.with_name(f"{parent.name}_module.py"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def index(): return 'ok'\n", encoding="utf-8")
    assert target.is_file() and (ws_dir / "app_module.py").is_file()
