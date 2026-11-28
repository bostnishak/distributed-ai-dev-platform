"""v5 milestone 07: ceilings, clones, dead weight, layer rules, verified clean-up and accessibility."""

from __future__ import annotations

import ast

import pytest

import a11y
import arch_heal
import arch_scan

pytestmark = pytest.mark.unit

_LONG = "def karisik(x):\n" + "".join(f"    if x > {i}:\n        x -= 1\n" for i in range(12)) + "    return x\n"
_COPY = "def {name}({arg}):\n    toplam = 0\n    for parca in {arg}:\n        if parca:\n            toplam += parca\n    return toplam\n"


def _write(root, files):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")


def _kinds(findings):
    return {(f.kind, f.file, f.subject) for f in findings}


def test_scan_finds_each_kind_of_rot(tmp_path):
    _write(tmp_path, {
        "app.py": "import yardimci\n\n\n" + _LONG + "\n\nkarisik(3)\nyardimci.topla([1])\n",
        "yardimci.py": "import app\n\n\n" + _COPY.format(name="topla", arg="liste") + "\n\n" + _COPY.format(name="olu", arg="veri"),
        "ui/ekran.py": "import sqlite3\n",
        "services/odeme.py": "from fastapi import Request\n",
        "index.html": "<style>.kullanilan{color:#fff}.hayalet{color:#000}</style><div class='kullanilan'></div><script>fetch('/api/var')</script>",
        "api.py": "from fastapi import FastAPI\napp = FastAPI()\n\n\n@app.get('/api/var')\ndef var():\n    return 1\n\n\n@app.get('/api/yetim')\ndef yetim():\n    return 2\n",
        "unutulmus.js": "let x = 1;",
    })
    found = _kinds(arch_scan.scan(tmp_path))
    kinds = {k for k, _f, _s in found}
    assert {"döngüsel içe aktarma", "katman ihlali", "karmaşıklık", "kopya kod", "ölü kod", "kullanılmayan CSS", "yetim dosya", "yetim uç nokta"} <= kinds
    assert ("ölü kod", "yardimci.py", "olu") in found and ("ölü kod", "app.py", "karisik") not in found
    assert ("kullanılmayan CSS", "index.html", ".hayalet") in found and ("kullanılmayan CSS", "index.html", ".kullanilan") not in found
    assert ("yetim uç nokta", "api.py", "/api/yetim") in found and ("yetim uç nokta", "api.py", "/api/var") not in found
    assert any("ui/ekran.py" in line for line in arch_scan.blocking(tmp_path)) and len(arch_scan.blocking(tmp_path)) == 3


def test_heal_removes_rot_and_keeps_behaviour(tmp_path):
    _write(tmp_path, {
        "hesap.py": _COPY.format(name="topla", arg="liste") + "\n\ndef olu():\n    return 1\n",
        "rapor.py": _COPY.format(name="topla", arg="liste") + "\n\ndef yaz():\n    return topla([1, 2])\n",
        "main.py": "import hesap\nimport rapor\n\nprint(hesap.topla([3]), rapor.yaz())\n",
        "style.css": ".var{color:red}\n.yok, .var{margin:0}\n.hic{padding:0}\n",
        "index.html": "<link rel='stylesheet' href='style.css'><p class='var'></p>",
    })
    done = arch_heal.heal(tmp_path)
    assert len(done) == 3
    assert "from hesap import topla" in (tmp_path / "rapor.py").read_text(encoding="utf-8")
    assert "def olu" not in (tmp_path / "hesap.py").read_text(encoding="utf-8")
    css = (tmp_path / "style.css").read_text(encoding="utf-8")
    assert ".var" in css and ".yok" not in css and ".hic" not in css
    scope: dict = {}
    exec(compile((tmp_path / "hesap.py").read_text(encoding="utf-8"), "hesap", "exec"), scope)  # noqa: S102, RUF100  # the test's own sample
    assert scope["topla"]([1, 2]) == 3
    assert arch_heal.heal(tmp_path) == []


def test_heal_is_undone_when_the_project_check_fails(tmp_path):
    _write(tmp_path, {"a.py": "def olu():\n    return 1\n"})
    assert arch_heal.heal(tmp_path, check=lambda: False) == []
    assert "def olu" in (tmp_path / "a.py").read_text(encoding="utf-8")


def test_long_module_is_split_and_callers_keep_working(tmp_path):
    body = "".join(f"def f{i}(x):\n" + "    x += 1\n" * 20 + "    return x\n\n\n" for i in range(16))
    _write(tmp_path, {"buyuk.py": body + "def hepsi():\n    return " + " + ".join(f"f{i}(0)" for i in range(16)) + "\n", "main.py": "from buyuk import f0, hepsi\nprint(hepsi(), f0(1))\n"})
    done = arch_heal.split_long_modules(tmp_path)
    assert done and (tmp_path / "buyuk_helpers.py").is_file()
    for name in ("buyuk.py", "buyuk_helpers.py"):
        text = (tmp_path / name).read_text(encoding="utf-8")
        ast.parse(text)
        assert text.count("\n") <= arch_scan.MAX_FILE_LINES
    assert "from buyuk_helpers import" in (tmp_path / "buyuk.py").read_text(encoding="utf-8")


_BAD_PAGE = """<!doctype html><html><head><title>x</title></head><body style="background:#fff">
<p style="color:#ddd">soluk yazı</p><input type="text"><div onclick="1">tıkla</div><button>aç</button>
<div role="dialog" aria-label="Pencere" hidden id="d"><button>tamam</button></div><a href="#z">dış bağlantı</a>
<script>document.querySelector('button').onclick = () => document.getElementById('d').hidden = false;</script></body></html>"""
_GOOD_PAGE = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Notlar</title></head><body><main><h1>Notlar</h1>
<label for="n">Not</label><input id="n"><button>Ekle</button></main></body></html>"""


def test_accessibility_audit_on_a_real_page(tmp_path):
    if not a11y.axe_script().is_file():
        pytest.skip("axe-core kasada yok (scripts/vendor_fetch.py)")
    (tmp_path / "bad.html").write_text(_BAD_PAGE, encoding="utf-8")
    (tmp_path / "index.html").write_text(_GOOD_PAGE, encoding="utf-8")
    bad = a11y.audit((tmp_path / "bad.html").as_uri())
    if bad is None:
        pytest.skip("tarayıcı çalıştırılamadı")
    joined = " | ".join(bad)
    assert "color-contrast" in joined and "label" in joined and "klavye sırasına girmeyen" in joined and "odak" in joined and "Escape" in joined
    assert a11y.audit((tmp_path / "index.html").as_uri()) == []


def test_automatic_cleanup_removes_only_what_the_edit_orphaned(tmp_path):
    _write(tmp_path, {"a.py": "def eski_yardimci():\n    return 1\n\n\ndef istenen():\n    return 2\n\n\nprint(eski_yardimci())\n",
                      "style.css": ".kart{color:red}\n.hazir{margin:0}\n", "index.html": "<div class='kart'></div>"})
    before = arch_heal.alive(tmp_path)
    (tmp_path / "a.py").write_text((tmp_path / "a.py").read_text(encoding="utf-8").replace("print(eski_yardimci())", "print(3)"), encoding="utf-8")
    (tmp_path / "index.html").write_text("<div></div>", encoding="utf-8")
    done = arch_heal.heal(tmp_path, used_before=before)
    assert len(done) == 2
    code, css = (tmp_path / "a.py").read_text(encoding="utf-8"), (tmp_path / "style.css").read_text(encoding="utf-8")
    assert "eski_yardimci" not in code and "def istenen" in code
    assert ".kart" not in css and ".hazir" in css


def test_oversized_function_is_split_only_when_the_split_helps(tmp_path):
    import asyncio

    _write(tmp_path, {"a.py": _LONG + "\n\nprint(karisik(30))\n"})
    small = "def _azalt(x, i):\n    return x - 1 if x > i else x\n\n\ndef karisik(x):\n    for i in range(12):\n        x = _azalt(x, i)\n    return x\n\n\nprint(karisik(30))\n"
    answers = iter(["```python\n" + _LONG + "```", "```python\n" + small + "```"])

    async def generate(system, user):
        return next(answers)

    done = asyncio.run(arch_heal.decompose(tmp_path, generate))
    assert len(done) == 1 and (tmp_path / "a.py").read_text(encoding="utf-8").strip() == small.strip()
    assert arch_scan.ceilings(tmp_path) == []


_NOTES = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>N</title></head><body>
<input id="q" placeholder="Ara"><input id="n" aria-label="Not"><button id="e">Ekle</button><ul id="l"></ul>
<script>
const items = JSON.parse(localStorage.getItem('n') || '[]');
function render() { document.getElementById('l').replaceChildren(...items.map(x => { const li = document.createElement('li'); li.textContent = x; return li; })); }
document.getElementById('e').addEventListener('click', () => { const v = document.getElementById('n').value.trim(); if (!v) return; items.push(v); localStorage.setItem('n', JSON.stringify(items)); render(); });
render();
</script></body></html>"""
_BROKEN = _NOTES.replace("if (!v) return;", "if (!v) { return;")


def _health(tmp_path, page):
    import edit_guard

    (tmp_path / "index.html").write_text(page, encoding="utf-8")
    measured = edit_guard.health(tmp_path)
    if measured is None:
        pytest.skip("tarayıcı çalıştırılamadı")
    return measured


def test_health_sees_what_a_change_broke(tmp_path):
    import edit_guard

    good = _health(tmp_path, _NOTES)
    assert (good.errors, good.adds, good.persists) == ((), True, True), "arama kutusu not alanı sanılmaz"
    broken = _health(tmp_path, _BROKEN)
    said = edit_guard.worse(good, broken)
    assert "JavaScript hatası" in said and "ekleme" in said
    assert "betik1.js" not in edit_guard.syntax_error(_BROKEN) and edit_guard.syntax_error(_NOTES) == ""
    assert edit_guard.worse(good, _health(tmp_path, _NOTES.replace("localStorage.setItem('n', JSON.stringify(items)); ", ""))) == "kayıtlar artık yenileyince kayboluyor"
    assert edit_guard.worse(broken, good) == ""


@pytest.mark.parametrize(("answers", "kept", "word"), [([_NOTES.replace("<title>N", "<title>Onarıldı")], "Onarıldı", "onarıldı"), ([_BROKEN, _BROKEN], "<title>N<", "uygulanmadı")])
def test_breaking_change_is_repaired_or_rolled_back(tmp_path, answers, kept, word):
    import asyncio

    import edit_guard

    before = (_health(tmp_path, _NOTES), _NOTES)
    (tmp_path / "index.html").write_text(_BROKEN, encoding="utf-8")
    replies = iter(answers)
    asked: list[str] = []

    async def generate(system, user):
        asked.append(user)
        return "```html\n" + next(replies) + "\n```"

    lines = asyncio.run(edit_guard.guard(tmp_path, before, "başlığı değiştir", generate))
    assert word in lines[0] and kept in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert (tmp_path / edit_guard.REJECTED).is_file() == (word == "uygulanmadı")
    assert "ÖLÇÜLEN SORUN" in asked[0] and (len(asked) < 2 or "TEKRARLAMA" in asked[1])


def test_a_new_page_that_logs_errors_is_repaired_or_reported(tmp_path):
    import asyncio

    import edit_guard

    noisy = _NOTES.replace("render();\n</script>", "render();\nconsole.error('Diyagram: nodes tanımsız');\n</script>")
    assert noisy != _NOTES
    assert _health(tmp_path, noisy).errors == ("Diyagram: nodes tanımsız",)

    async def fixes(system, user):
        assert "Diyagram: nodes tanımsız" in user
        return "```html\n" + _NOTES + "\n```"

    async def useless(system, user):
        return "```html\n" + noisy + "\n```"

    assert "onarıldı" in asyncio.run(edit_guard.settle(tmp_path, "pano", fixes))[0]
    assert asyncio.run(edit_guard.settle(tmp_path, "pano", fixes)) == []
    (tmp_path / "index.html").write_text(noisy, encoding="utf-8")
    assert asyncio.run(edit_guard.settle(tmp_path, "pano", useless))[0].startswith("Uyarı")
