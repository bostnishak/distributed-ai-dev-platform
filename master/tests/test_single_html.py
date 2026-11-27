"""One-file web requests stay web, one file, previewable; layout words do not make them desktop programs."""

import pytest

import assistant_cad_cnc
import workspace_batches
import workspace_kit

pytestmark = pytest.mark.unit
_SPEC = 'Tek sayfalık, tek bir HTML dosyası içinde panel. Sol panel masaüstünde 260px. Örnek: "API Gateway Health Check". bunu yap'


def test_spec_is_a_single_web_page():
    assert workspace_batches.wants_single_html(_SPEC)
    assert assistant_cad_cnc.detect_project_type(_SPEC) == ("web", False)


def test_layout_words_are_not_a_desktop_program():
    assert assistant_cad_cnc.detect_project_type("web paneli yap, masaüstünde 3 sütun olsun") == ("web", False)
    assert assistant_cad_cnc.detect_project_type("masaüstü uygulaması olarak not defteri yap")[1] is True


def test_self_contained_page_is_not_restyled(tmp_path):
    page = tmp_path / "index.html"
    page.write_text("<html><head><style>body{color:red}</style></head><body></body></html>", encoding="utf-8")
    assert workspace_kit.inject_theme(tmp_path) is False and not (tmp_path / "css").exists()
