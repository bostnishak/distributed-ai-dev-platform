"""LibreOffice verification of delivered files and Z3 confirmation of numeric answers."""

import asyncio

import openpyxl
import pytest

import office_verify
import z3_math

pytestmark = pytest.mark.unit


def _book(tmp_path, formula):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Veri"
    sheet.append([10, 0])
    sheet["C1"] = formula
    path = tmp_path / "x.xlsx"
    book.save(path)
    return path


@pytest.mark.parametrize(("formula", "broken"), [("=A1/B1", True), ("=A1+B1", False), ("=Yok!A1", True)])
def test_libreoffice_recalculates_and_finds_error_cells(tmp_path, formula, broken):
    if not office_verify.soffice():
        pytest.skip("LibreOffice yok")
    found = office_verify.check(_book(tmp_path, formula))
    assert found is not None and bool(found) is broken


def test_z3_returns_only_unique_values():
    unique = z3_math.Model(variables={"x": "int", "y": "int"}, constraints=["x + y == 10", "x - y == 2"], ask="x")
    assert z3_math.solve(unique) == 6.0
    assert z3_math.solve(z3_math.Model(variables={"x": "int"}, constraints=["x > 3"], ask="x")) is None
    assert z3_math.solve(z3_math.Model(variables={"x": "int"}, constraints=["__import__('os').system('x') == 0"], ask="x")) is None


def test_confirmation_flags_a_wrong_answer():
    async def chat(system, user, schema, num_ctx):
        return '{"variables": {"x": "int"}, "constraints": ["2*x == 14"], "ask": "x"}'

    assert "doğrulandı" in asyncio.run(z3_math.confirm("soru", "Sonuç: 7", chat))
    assert "uyuşmuyor" in asyncio.run(z3_math.confirm("soru", "Sonuç: 9", chat))


def test_judge_commentary_is_removed_from_the_answer():
    import reasoning_mode

    text = "1. Toplam 20 baş.\n2. Aday 3'ün adımları daha sistematik, diğer adaylar da doğru.\nÇiftlikte 8 koyun vardır."
    out = reasoning_mode.without_judge_talk(text)
    assert "Aday" not in out and "8 koyun" in out and "Toplam 20 baş" in out
