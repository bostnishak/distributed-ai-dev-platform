"""Page text extraction and sentence ranking for web-grounded answers (no network)."""

from __future__ import annotations

import pytest

import page_facts as pf

pytestmark = pytest.mark.unit

HTML = (
    b"<html><head><style>x{}</style><script>var a=1;</script></head><body><nav>Menu Anasayfa</nav>"
    b"<p>EPDK verilerine g\xc3\xb6re T\xc3\xbcrkiye'deki \xc5\x9farj soketi say\xc4\xb1s\xc4\xb1 48 bin 971'e y\xc3\xbckseldi.</p>"
    b"<p>Bug\xc3\xbcn hava \xc3\xa7ok g\xc3\xbczel ve g\xc3\xbcne\xc5\x9fli bir g\xc3\xbcn olarak ge\xc3\xa7ecek gibi g\xc3\xb6r\xc3\xbcn\xc3\xbcyor.</p>"
    b"<footer>Telif</footer></body></html>"
)


def test_text_extraction_drops_scripts_and_navigation():
    text = pf._text(HTML, "utf-8")
    assert "var a" not in text and "Menu" not in text and "48 bin 971" in text


def test_sentences_about_the_question_win():
    terms = {"şarj", "soket"}
    out = pf.best_sentences(pf._text(HTML, "utf-8"), terms)
    assert "48 bin 971" in out and "hava" not in out


def test_private_hosts_are_never_fetched():
    assert pf.fetch_text("http://127.0.0.1:8000/") == "" and pf.fetch_text("file:///etc/passwd") == ""
