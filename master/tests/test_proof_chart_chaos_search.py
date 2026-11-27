"""Z3 proofs, charts from real data, random-click testing, code search and diagram exports."""

import pytest

import code_search
import data_chart
import flowchart_studio
import symbolic
import ui_chaos

pytestmark = pytest.mark.unit

_ACCOUNT = "\n".join([
    "class Account:",
    "    def __init__(self):",
    "        self.balance = 0",
    "",
    "    def deposit(self, amount):",
    "        if amount <= 0:",
    "            raise ValueError('positive')",
    "        self.balance += amount",
    "",
    "    def withdraw(self, amount):",
    "        if amount <= 0:",
    "            raise ValueError('positive')",
    "        self.balance -= amount",
    "",
])
_FIXED = _ACCOUNT.replace("        self.balance -= amount", "        if amount > self.balance:\n            raise ValueError('yetersiz')\n        self.balance -= amount")


def test_z3_finds_the_input_that_breaks_the_rule_and_proves_the_fix(tmp_path):
    (tmp_path / "account.py").write_text(_ACCOUNT, encoding="utf-8")
    broken = symbolic.report(tmp_path, "Bakiye asla negatif olamaz")
    assert "İHLAL" in broken and "Account.withdraw" in broken and "balance=" in broken and "deposit" not in broken
    (tmp_path / "account.py").write_text(_FIXED, encoding="utf-8")
    proved = symbolic.report(tmp_path, "Bakiye asla negatif olamaz")
    assert "İSPATLANDI" in proved and "Account.withdraw" in proved and "Account.deposit" in proved


def test_unsupported_code_is_never_called_proved(tmp_path):
    looped = _ACCOUNT.replace("        self.balance -= amount", "        for _ in range(amount):\n            self.balance -= 1")
    (tmp_path / "account.py").write_text(looped, encoding="utf-8")
    assert "İspatlanamayan" in symbolic.report(tmp_path, "bakiye negatif olamaz")
    assert symbolic.report(tmp_path, "kullanıcı adı boş olmamalı") == ""


def test_chart_groups_the_real_rows():
    rows = [{"sehir": "Ankara", "satis": "10"}, {"sehir": "İzmir", "satis": "5"}, {"sehir": "Ankara", "satis": "30"}]
    assert data_chart.aggregate(rows, "şehir bazında grafik")[2] == [("Ankara", 40.0), ("İzmir", 5.0)]
    assert data_chart.aggregate(rows, "ortalama satis grafiği")[2][0] == ("Ankara", 20.0)
    assert data_chart.aggregate([{"ad": "a"}], "grafik") is None


def test_random_clicking_finds_a_crash_on_an_empty_input(tmp_path):
    pytest.importorskip("playwright")
    page = tmp_path / "index.html"
    page.write_text("<input id=n><button onclick=\"const v=document.getElementById('n').value; v.trim().split(' ')[1].toUpperCase()\">Ekle</button>", encoding="utf-8")
    result = ui_chaos.report(tmp_path)
    if result is None:
        pytest.skip("tarayıcı yok")
    assert "yakalanmamış hata" in result
    page.write_text("<button onclick=\"this.textContent='ok'\">Ekle</button>", encoding="utf-8")
    assert ui_chaos.report(tmp_path) == ""


def test_code_search_ranks_the_right_file(tmp_path):
    (tmp_path / "mail.py").write_text("def send_invoice_mail(address):\n    return address\n", encoding="utf-8")
    (tmp_path / "stock.py").write_text("def count_stock(items):\n    return len(items)\n", encoding="utf-8")

    def embed(texts):
        return [[1.0, 0.0] if ("mail" in t or "fatura" in t) else [0.0, 1.0] for t in texts]

    assert code_search.search(tmp_path, "fatura gönderme mail", embed=embed)[0][0] == "mail.py"
    assert code_search.asked("projede stok sayımı nerede yapılıyor?") == "stok sayımı"
    assert code_search.asked("stok nerede") == ""


def test_diagram_exports_share_the_same_structure():
    flow = {"steps": [{"id": "a", "type": "start", "label": "Başla"}, {"id": "b", "type": "decision", "label": 'Stok "var" mı?'}, {"id": "c", "type": "end", "label": "Bitir"}],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c", "label": "Evet"}]}
    out = flowchart_studio.exports(flow)
    assert out["mmd"].startswith("flowchart TD") and "-->|Evet| n3" in out["mmd"] and '"Stok  var  mı?"' in out["mmd"]
    assert 'n2 -> n3 [label="Evet"];' in out["dot"] and out["puml"].startswith("@startuml") and "n2 --> n3 : Evet" in out["puml"]
