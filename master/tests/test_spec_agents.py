"""Surgical patches, the intake/architect agents, size checks and the API probe."""

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

import agent_contracts
import patch_edit
import spec_contract

pytestmark = pytest.mark.unit
_FILE = "<html>\n  <body>\n    <button>Ekle</button>\n  </body>\n</html>\n"


class _Item(BaseModel):
    name: str


def test_patch_applies_only_unique_blocks():
    blocks = patch_edit.parse("<<<<<<< SEARCH\n<button>Ekle</button>\n=======\n<button>Kaydet</button>\n>>>>>>> REPLACE")
    assert "<button>Kaydet</button>" in patch_edit.apply(_FILE, blocks)
    assert patch_edit.apply(_FILE, [("yok", "x")]) is None
    assert patch_edit.apply("a\na\n", [("a", "b")]) is None


def test_patch_that_drops_the_page_end_is_refused():
    page = _FILE + "<!--" + "x" * 2000 + "-->"

    async def generate(system, user):
        return "<<<<<<< SEARCH\n  </body>\n</html>\n=======\n  </body>\n>>>>>>> REPLACE"

    assert asyncio.run(patch_edit.try_patch(generate, "a", page)) is None


def test_intake_keeps_only_buttons_the_user_named():
    async def chat(system, user, schema, num_ctx):
        return '{"buttons": [{"label": "Ekle", "behavior": "ekler"}, {"label": "Paylaş", "behavior": "x"}]}'

    spec = asyncio.run(agent_contracts.intake('"Ekle" butonu, panel 260px, arka plan #0F172A', chat))
    assert [b.label for b in spec.buttons] == ["Ekle"] and spec.sizes == ["260px"] and spec.colors == ["#0F172A"]
    assert "'Ekle' düğmesi: ekler" in agent_contracts.writer_notes(spec)


def test_invalid_model_answer_invents_nothing():
    async def chat(system, user, schema, num_ctx):
        return "olur, harika fikir"

    assert asyncio.run(agent_contracts.review("x", chat)).warnings == []


def test_missing_size_is_reported(tmp_path):
    (tmp_path / "index.html").write_text("<style>aside{width:200px}</style>", encoding="utf-8")
    assert "260px" in spec_contract.problem(tmp_path, "sol panel 260px olsun")[1]


def _check_fastapi():
    scope: dict = {}
    source = (Path(__file__).parent.parent / "prompts" / "api_probe.py.txt").read_text(encoding="utf-8")
    exec(compile(source, "api_probe", "exec"), scope)
    return scope["check_fastapi"]


def test_api_probe_passes_a_validating_endpoint():
    app = FastAPI()

    @app.post("/things", status_code=201)
    def add(item: _Item):
        return item

    _check_fastapi()(app)


def test_api_probe_rejects_a_crashing_endpoint():
    app = FastAPI()

    @app.get("/boom")
    def boom():
        raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        _check_fastapi()(app)
