"""A page that links a stylesheet by the wrong relative path gets the link repaired (or the shared theme written)."""

from __future__ import annotations

import pytest

import workspace_requirements as wr

pytestmark = pytest.mark.unit


def test_link_is_pointed_at_the_existing_file(tmp_path):
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "theme.css").write_text("body{}", encoding="utf-8")
    page = tmp_path / "index.html"
    page.write_text('<link rel="stylesheet" href="theme.css"><script src="js/app.js"></script>', encoding="utf-8")
    wr._fix_missing_local_refs(tmp_path)
    assert 'href="css/theme.css"' in page.read_text(encoding="utf-8")


def test_missing_theme_is_written_from_the_kit(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<link rel="stylesheet" href="theme.css">', encoding="utf-8")
    wr._fix_missing_local_refs(tmp_path)
    assert (tmp_path / "theme.css").is_file()


def test_listeners_on_missing_elements_no_longer_crash_the_script(tmp_path):
    js = tmp_path / "app.js"
    js.write_text("document.getElementById('a').addEventListener('click', f);\nconst b = document.querySelector('.x');\nb.addEventListener('click', g);\nwindow.addEventListener('load', h);\n", encoding="utf-8")
    wr._null_safe_listeners(tmp_path)
    out = js.read_text(encoding="utf-8")
    assert "getElementById('a')?.addEventListener" in out and "b?.addEventListener" in out and "window.addEventListener" in out


def test_es_module_syntax_is_removed_from_classic_scripts(tmp_path):
    (tmp_path / "index.html").write_text('<script src="app.js"></script><script type="module" src="m.js"></script>', encoding="utf-8")
    (tmp_path / "app.js").write_text("import { x } from './utils.js';\nexport function f() {}\nexport default class A {}\nexport { f };\nconst y = 1;\n", encoding="utf-8")
    (tmp_path / "m.js").write_text("export const z = 1;\n", encoding="utf-8")
    wr._classic_scripts(tmp_path)
    out = (tmp_path / "app.js").read_text(encoding="utf-8")
    assert "import" not in out and "export" not in out and "function f()" in out and "class A" in out
    assert "export const z" in (tmp_path / "m.js").read_text(encoding="utf-8")


def test_keypad_label_follows_the_digit_the_button_carries(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<button data-value="9">*</button><button data-value="*">*</button><button data-value="7">7</button>', encoding="utf-8")
    wr._sync_key_labels(tmp_path)
    out = page.read_text(encoding="utf-8")
    assert '<button data-value="9">9</button>' in out and '<button data-value="*">*</button>' in out
