"""v5 milestone 06: the reality torture suite passes a correct page and catches the injected bugs (real browser)."""

from __future__ import annotations

import pytest

import torture

pytestmark = pytest.mark.integration

GOOD = """<!doctype html><html><head><meta charset="utf-8"><title>Harcama</title><link rel="icon" href="data:,"></head><body><main>
<h1>Harcama defteri</h1><input id="m" aria-label="Açıklama"><input id="t" type="number" step="0.01" aria-label="Tutar"><button id="e">Ekle</button>
<input id="a" type="search" aria-label="Ara"><p id="s"></p><ul id="l"></ul></main>
<script>
const items = []; const $ = id => document.getElementById(id);
function render() {
  const q = $('a').value.toLocaleLowerCase('tr');
  $('l').replaceChildren(...items.filter(x => x.text.toLocaleLowerCase('tr').includes(q)).map(x => {
    const li = document.createElement('li'); li.textContent = x.text + ' — ' + (x.cents / 100).toFixed(2); return li; }));
  $('s').textContent = 'Toplam: ' + (items.reduce((sum, x) => sum + x.cents, 0) / 100).toFixed(2);
}
$('e').addEventListener('click', () => {
  const text = $('m').value.trim(); if (!text) return;
  items.push({text, cents: Math.round(Number($('t').value || 0) * 100)}); $('m').value = ''; $('t').value = ''; render();
});
$('a').addEventListener('input', render); render();
</script></body></html>"""

FLOAT_MONEY = GOOD.replace("cents: Math.round(Number($('t').value || 0) * 100)", "cents: Number($('t').value || 0)").replace("(x.cents / 100).toFixed(2)", "x.cents").replace(
    "(items.reduce((sum, x) => sum + x.cents, 0) / 100).toFixed(2)", "items.reduce((sum, x) => sum + x.cents, 0)")
DOUBLE_SUBMIT = GOOD.replace("items.push({text, cents: Math.round(Number($('t').value || 0) * 100)}); $('m').value = ''; $('t').value = ''; render();",
                             "setTimeout(() => { items.push({text, cents: 0}); $('m').value = ''; render(); }, 300);")
ASCII_SEARCH = GOOD.replace("x.text.toLocaleLowerCase('tr')", "x.text.toLowerCase()").replace("$('a').value.toLocaleLowerCase('tr')", "$('a').value.toLowerCase()")
NAN_TOTAL = GOOD.replace("(x.cents / 100).toFixed(2); return li", "(x.cents / Math.sqrt(x.cents) / 100).toFixed(2); return li")
UNSAFE = GOOD.replace("li.textContent = x.text", "li.innerHTML = x.text")


def _run(tmp_path, page):
    (tmp_path / "index.html").write_text(page, encoding="utf-8")
    results = torture.run((tmp_path / "index.html").as_uri(), {**torture.QUICK, **torture.HEAVY})
    if results is None or all("denetim yapılamadı" in detail for _passed, detail in results.values()):
        pytest.skip("tarayıcı çalıştırılamadı")
    return results


def test_correct_page_survives_every_check(tmp_path):
    results = _run(tmp_path, GOOD)
    assert torture.failures(results) == []
    assert sum(passed is True for passed, _ in results.values()) == len(results)


@pytest.mark.parametrize(("page", "check"), [(FLOAT_MONEY, "para hesabı"), (DOUBLE_SUBMIT, "çift gönderim"), (ASCII_SEARCH, "Türkçe arama"), (UNSAFE, "özel karakter ve XSS"), (NAN_TOTAL, "sayı ve tarih sınırları")])
def test_each_injected_bug_is_caught_by_its_check(tmp_path, page, check):
    assert page != GOOD
    results = _run(tmp_path, page)
    assert results[check][0] is False, results[check]


def test_page_without_a_form_is_not_judged_on_form_checks(tmp_path):
    results = _run(tmp_path, "<!doctype html><meta charset='utf-8'><p>Yalnız bir metin sayfası, toplam NaN</p>")
    assert results["çift gönderim"][0] is None and results["boş durum"][0] is False


def test_failures_names_only_what_failed():
    assert torture.failures({"a": (True, ""), "b": (None, "yok"), "c": (False, "bozuk")}) == ["c: bozuk"]


def test_data_bugs_block_delivery_and_network_manners_only_warn():
    status, detail = torture.judged(("geçti", "ok"), {"çift gönderim": (False, "3 kayıt"), "yavaş ağ": (False, "kilit yok")}, "kaldı")
    assert status == "kaldı" and "3 kayıt" in detail
    status, detail = torture.judged(("geçti", "ok"), {"yavaş ağ": (False, "kilit yok"), "para hesabı": (True, "")}, "kaldı")
    assert status == "geçti" and "uyarısı" in detail and "kilit yok" in detail
    assert torture.judged(("geçti", "ok"), None, "kaldı") == ("geçti", "ok")
