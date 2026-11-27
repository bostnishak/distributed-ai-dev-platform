"""Language server references and message framing."""

import io

import pytest

import lsp_client
import protocol_io

pytestmark = pytest.mark.unit


def test_framed_messages_round_trip():
    out = io.BytesIO()
    channel = protocol_io.Channel(io.BytesIO(b""), out)
    channel.send({"a": "ğ"})
    back = protocol_io.Channel(io.BytesIO(out.getvalue()), io.BytesIO())
    assert back.wait(lambda m: True, 3) == {"a": "ğ"}
    with pytest.raises(TimeoutError):
        back.wait(lambda m: True, 0.2)


def test_a_real_language_server_finds_every_use(tmp_path):
    pytest.importorskip("pylsp")
    pytest.importorskip("jedi")
    tmp_path = tmp_path / "Okul projeleri şu klasör"
    tmp_path.mkdir()
    (tmp_path / "store.py").write_text("import json\n\n\ndef load_orders():\n    return []\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("from store import load_orders\n\n\ndef main():\n    # load_orders in a comment is not a use\n    return load_orders()\n", encoding="utf-8")
    found = lsp_client.references(tmp_path, "load_orders")
    assert [(name, row) for name, row, _ in found] == [("app.py", 1), ("app.py", 6), ("store.py", 4)]
    assert lsp_client.references(tmp_path, "missing_name") is None


def test_a_planted_module_in_the_project_is_not_executed(tmp_path):
    pytest.importorskip("pylsp")
    (tmp_path / "pylsp.py").write_text("open('owned.txt', 'w').write('x')\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    assert lsp_client.references(tmp_path, "f")
    assert not (tmp_path / "owned.txt").exists()


@pytest.mark.parametrize(("text", "symbol"), [
    ("load_orders nerede kullanılıyor?", "load_orders"), ("find references of main", "main"), ("bu butonu nerede kullanıyorum", ""),
])
def test_reference_question(text, symbol):
    assert lsp_client.asked_symbol(text) == symbol
