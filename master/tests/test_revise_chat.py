"""Change requests in chat edit the project already built; questions and new projects do not."""

import json

import pytest

import revise_chat
import workspace_batches

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text", ["şuraları düzelt", "butonlar çalışmıyor", "arka planı beyaz yap", "bir arama kutusu ekle", "make the header blue"])
def test_change_requests(text):
    assert revise_chat.is_revision(text)


@pytest.mark.parametrize("text", ["bu kod nasıl çalışıyor?", "yeni bir uygulama yap: not defteri", "bunu pdf yap", "teşekkürler"])
def test_other_messages(text):
    assert not revise_chat.is_revision(text)


def test_workspace_comes_from_history():
    history = json.dumps([{"role": "assistant", "workspace": {"workspace": {"id": "abc-1"}, "tree": []}}, {"role": "user", "text": "x"}])
    assert revise_chat.last_workspace_id(history) == "abc-1"
    assert revise_chat.last_workspace_id("[]") == ""


async def _cut_off(ws_dir, model, spec, ask):
    return "<html><body>"


def test_cut_off_rewrite_keeps_the_working_page(tmp_path):
    import asyncio

    page = "<html><style></style></html>"
    out = asyncio.run(workspace_batches.apply_edit(_cut_off, (tmp_path, "m", "a"), {"path": "index.html"}, page))
    assert out == page and (tmp_path / "index.html").read_text(encoding="utf-8") == page
