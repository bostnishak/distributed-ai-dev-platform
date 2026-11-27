"""Long-document selection, proportionality governor and design hints."""

import pytest

import complexity_governor
import design_slop
import long_doc

pytestmark = pytest.mark.unit


def test_fact_deep_inside_a_long_document_is_found_with_its_line():
    lines = [f"Satır {i}: genel açıklama metni, ayrıntı yok." for i in range(3000)]
    lines[2400] = "Depo yangın sigortası poliçe numarası ZX-4471 olup bitiş tarihi 14 Mart 2027'dir."
    out = long_doc.select("\n".join(lines), "yangın sigortasının poliçe numarası nedir?", 8000)
    assert "ZX-4471" in out and len(out) <= 8000 and "[satır " in out


def test_short_documents_are_untouched():
    assert long_doc.select("kısa metin", "soru", 8000) == "kısa metin"


@pytest.mark.parametrize(
    ("prompt", "editing", "level"),
    [
        ("Ankara'nın nüfusu kaç?", False, 0),
        ("butonun rengini #10B981 yap", True, 0),
        ("listeye arama kutusu ekle", True, 1),
        ("bir hesap makinesi uygulaması yap", False, 2),
        ("ödeme ve kimlik doğrulama içeren mikroservis projesi yap", False, 3),
        ("@fast bir panel uygulaması yap " + "ayrıntı " * 60, False, 1),
        ("@derin kısa uygulama", False, 3),
    ],
)
def test_gears(prompt, editing, level):
    assert complexity_governor.classify(prompt, editing=editing).level == level


def test_override_words_are_removed_from_the_request():
    assert complexity_governor.strip_override("@fast bir oyun yap") == "bir oyun yap"


def test_template_design_markers_are_hinted_only_when_not_asked(tmp_path):
    (tmp_path / "index.html").write_text("<style>body{background:linear-gradient(#667eea,#764ba2)}</style><h1>Unleash the power of data</h1>", encoding="utf-8")
    found = design_slop.findings(tmp_path, "bir panel yap")
    assert len(found) == 2 and design_slop.findings(tmp_path, "mor gradyanlı panel") == [found[1]]


def test_small_api_requests_get_one_module():
    import workspace_batches

    plan = workspace_batches.fixed_plan("FastAPI ve SQLite kullanan bir not API projesi yap: POST /notes ve GET /notes.")
    assert plan["entry_point"] == "app.py" and [f["path"] for f in plan["files"]] == ["app.py", "requirements.txt", "README.md"]
    assert workspace_batches.fixed_plan("FastAPI API ve React arayüzü olan bir proje yap") is None
    assert workspace_batches.fixed_plan("FastAPI API: backend/models.py ve backend/main.py ile yap") is None


def test_files_at_the_disk_root_become_project_files(tmp_path):
    import workspace_requirements

    app = tmp_path / "app.py"
    app.write_text("LOG = '/server.log'\nURL = '/notes'\n", encoding="utf-8")
    workspace_requirements.repair_project(tmp_path)
    assert app.read_text(encoding="utf-8") == "LOG = 'server.log'\nURL = '/notes'\n"
