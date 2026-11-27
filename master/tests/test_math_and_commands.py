"""SymPy answers, model-free rename and undo."""

import pytest

import math_kernel
import refactor
import workspace_commands

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(("prompt", "expected"), [
    ("x^2*sin(x) türevini al", "x*(x*cos(x) + 2*sin(x))"),
    ("2x^2 - 8 = 0 denklemini çöz", "x = `-2`"),
    ("x^2 - 5x + 6 ifadesini çarpanlarına ayır", "(x - 3)*(x - 2)"),
    ("integral of 3x^2", "x^3 + C"),
])
def test_exact_symbolic_answers(prompt, expected):
    pytest.importorskip("sympy")
    assert expected in math_kernel.answer(prompt)


@pytest.mark.parametrize("prompt", [
    "bu kod hatasını çöz", "__import__('os') türevini al", "x.__class__ sadeleştir", "x^999999999 türevini al",
    "Türev ürünleri nedir", "satış verilerini sadeleştir",
])
def test_everything_else_is_left_to_the_model(prompt):
    assert math_kernel.parse(prompt) is None


def test_rename_changes_names_but_not_strings_or_comments(tmp_path):
    (tmp_path / "a.py").write_text("def calc(x):\n    # calc is old\n    return 'calc'\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("from a import calc\n\nprint(calc(1))\n", encoding="utf-8")
    assert refactor.rename(tmp_path, "calc", "compute") == ["a.py", "b.py"]
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "def compute(x):\n    # calc is old\n    return 'calc'\n"
    assert "from a import compute" in (tmp_path / "b.py").read_text(encoding="utf-8")


def test_rename_refuses_a_taken_name_and_changes_nothing(tmp_path):
    (tmp_path / "a.py").write_text("def one():\n    return two()\n\ndef two():\n    return 2\n", encoding="utf-8")
    before = (tmp_path / "a.py").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="zaten"):
        refactor.rename(tmp_path, "one", "two")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == before


@pytest.mark.parametrize(("prompt", "parsed"), [
    ("geri al", ("undo", "")), ("son değişikliği geri al", ("undo", "")), ("v2'ye dön", ("version", "v2")),
    ("calc fonksiyonunun adını compute yap", ("rename", "calc compute")), ("rename function a1 to b2", ("rename", "a1 b2")),
    ("geri al butonu ekle", None), ("butonun rengini mavi yap", None),
])
def test_command_phrases(prompt, parsed):
    assert workspace_commands.parse(prompt) == parsed


def test_previous_version_follows_the_active_one():
    versions = [{"version": "v1"}, {"version": "v2"}, {"version": "v3"}]
    assert workspace_commands.previous_version(versions, "") == "v2"
    assert workspace_commands.previous_version(versions, "v2") == "v1"
    assert workspace_commands.previous_version(versions, "v1") == ""
