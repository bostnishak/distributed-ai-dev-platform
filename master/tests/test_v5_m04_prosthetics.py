"""v5 milestone 04: the small-model prosthetics (stream guard, requirement ledger, clean-slate repair, chunking)."""

from __future__ import annotations

import asyncio

import pytest

from gateway import stream_guard

pytestmark = pytest.mark.unit


class _Stream:
    """A provider whose first attempts loop; records how each attempt was asked for and how many were closed."""

    def __init__(self, scripts):
        self.scripts, self.options, self.closed = list(scripts), [], 0

    async def stream(self, model, messages, options, timeout_s):
        self.options.append(options)
        pieces = self.scripts.pop(0)
        try:
            for piece in pieces:
                yield {"type": "token", "content": piece}
            yield {"type": "done"}
        finally:
            self.closed += 1


def _run(provider):
    async def read():
        return [e async for e in stream_guard.watched(provider, "m", [], {"temperature": 0.2, "repeat_penalty": 1.06}, 5.0)]

    return asyncio.run(read())


def test_guard_recognises_degeneration_and_leaves_healthy_text_alone():
    assert stream_guard.find("devam " + " " * 500) == "boşluk taşması"
    assert stream_guard.find("başlık\n" + "  return value\n" * 14) == "aynı satır döngüsü"
    assert stream_guard.find("giriş " + "ve sonra yine aynı cümle geliyor. " * 40) == "tekrar eden blok"
    assert stream_guard.find("```python\nx = 1\n```\n" + "".join(f"Açıklama satırı {i} burada.\n" for i in range(40)), expect_code=True) == "kod bloğundan düz yazıya kayma"
    healthy = "".join(f"def fonksiyon_{i}(deger):\n    return deger * {i}\n\n" for i in range(40))
    assert stream_guard.find(healthy, expect_code=True) == ""
    table = "| Ay | Tutar |\n|---|---|\n" + "".join(f"| {i} | {i * 17} |\n" for i in range(80))
    assert stream_guard.find(table) == ""


def test_looping_stream_is_cut_early_and_retried_with_new_settings():
    loop = ["aynı satır\n"] * 500
    provider = _Stream([loop, ["temiz ", "yanıt"]])
    events = _run(provider)
    restart = next(e for e in events if e["type"] == "restart")
    assert restart["chars"] < 600 and provider.closed == 2
    assert provider.options[1]["repeat_penalty"] > provider.options[0]["repeat_penalty"]
    assert provider.options[1]["seed"] != provider.options[0].get("seed")
    after = events[events.index(restart) + 1 :]
    assert "".join(e.get("content", "") for e in after) == "temiz yanıt" and after[-1]["type"] == "done"


def test_last_attempt_is_never_cut():
    loop = ["aynı satır\n"] * 60
    provider = _Stream([loop, loop, loop])
    events = _run(provider)
    assert [e["type"] for e in events].count("restart") == stream_guard.RESTARTS
    assert events[-1]["type"] == "done"


def test_collect_returns_only_the_clean_attempt():
    class Client:
        async def stream(self, messages, **options):
            assert stream_guard.EXPECT_CODE.get() is True
            for event in ({"type": "token", "content": "bozuk"}, {"type": "restart"}, {"type": "token", "content": "sağlam"}, {"type": "done"}):
                yield event

    assert asyncio.run(stream_guard.collect(Client(), [], True, model="m")) == "sağlam"
    assert stream_guard.EXPECT_CODE.get() is False


def test_chat_stream_discards_what_a_cut_attempt_showed():
    import assistant_prep

    state = {"buffered": ["eski"], "need_buffer": True}
    lines = assistant_prep._handle_stream_event({"type": "restart", "reason": "x"}, state, str)
    assert state["buffered"] == [] and '"restart"' in lines[0]


_CONTRACT = {
    "colors": ["#0F172A", "#38BDF8", "#F8FAFC"], "sizes": ["64px"], "labels": ["Görev Panosu", "Ekle"], "regions": ["üst bar", "yan menü", "alt bilgi"],
    "buttons": [{"label": "Ekle", "behavior": "yazılan görevi listeye ekler"}, {"label": "Temizle", "behavior": "listeyi boşaltır"}],
    "forbidden": ["harici kütüphane", "alert kullanma"], "persistence": "görevler",
}
_ASK = "Boş girdi eklenmesin, mobil görünümde taşmasın."
_GOOD = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Görev Panosu</title>
<style>:root{--a:#0F172A;--b:#38BDF8;--c:#F8FAFC}header{height:64px;background:var(--a);color:#fff}aside,footer{display:block;padding:8px}@media(max-width:500px){aside{width:auto}}</style></head>
<body><header><h1>Görev Panosu</h1></header><aside>Menü</aside><main><input id="g"><button id="e">Ekle</button><button id="t">Temizle</button><ul id="l"></ul></main><footer>alt</footer>
<script>let items=JSON.parse(localStorage.getItem('g')||'[]');const l=document.getElementById('l');
function render(){l.replaceChildren(...items.map(x=>{const li=document.createElement('li');li.textContent=x;return li}));localStorage.setItem('g',JSON.stringify(items))}
document.getElementById('e').addEventListener('click',()=>{const g=document.getElementById('g');if(!g.value.trim())return;items.push(g.value);g.value='';render()});
document.getElementById('t').addEventListener('click',()=>{items=[];render()});render()</script></body></html>"""


def _verdicts(tmp_path, page):
    import req_checks
    import req_ledger

    (tmp_path / "index.html").write_text(page, encoding="utf-8")
    ledger = req_ledger.build(_CONTRACT, _ASK)
    found = req_checks.evaluate(tmp_path, ledger)
    if any("tarayıcı açılamadı" in detail for _passed, detail in found.values()):
        pytest.skip("tarayıcı çalıştırılamadı")
    return ledger, found


def test_ledger_numbers_every_constraint_in_slice_order():
    import req_ledger

    ledger = req_ledger.build(_CONTRACT, _ASK)
    assert [r.id for r in ledger] == [f"REQ-{i:03d}" for i in range(1, len(ledger) + 1)] and len(ledger) >= 15
    assert [r.slice for r in ledger] == sorted((r.slice for r in ledger), key=req_ledger.SLICES.index)
    assert not any(r.kind == "yazı" and r.target == "Ekle" for r in ledger), "düğme yazısı iki kez sayılmaz"
    assert len(req_ledger.upto(ledger, req_ledger.LAYOUT)) < len(req_ledger.upto(ledger, req_ledger.CONTROLS)) == len(ledger)


def test_every_requirement_is_met_by_a_correct_page(tmp_path):
    import req_checks

    ledger, found = _verdicts(tmp_path, _GOOD)
    assert req_checks.unmet(ledger, found) == []
    assert req_checks.score(found) == (len(ledger), len(ledger))


def test_broken_behaviour_is_pinned_to_its_requirement(tmp_path):

    broken = _GOOD.replace("if(!g.value.trim())return;", "").replace("localStorage.setItem('g',JSON.stringify(items))", "").replace("items=[];render()", "render()")
    broken = broken.replace("<footer>alt</footer>", "<script src='https://cdn.example.com/x.js'></script>")
    ledger, found = _verdicts(tmp_path, broken)
    failed = {r.kind + ":" + r.target for r in ledger if found[r.id][0] is False}
    assert {"kalıcılık:", "boş girdi:", "düğme:Temizle", "bölge:alt bilgi", "dış kaynak yok:harici kütüphane"} <= failed
    assert "renk:#0F172A" not in failed


def test_failed_approaches_are_banned_and_the_third_attempt_starts_clean():
    import clean_slate

    line = clean_slate.failed_approach("a\nb\n", "a\nitems.push(x)\nb\n", "Traceback\nTypeError: x is undefined")
    assert "items.push(x)" in line and "TypeError" in line and "\n" not in line
    fresh = clean_slate.prompt("REQ-001 [renk] #fff", "index.html", "<html></html>", "REQ-001 -> yok", [line])
    assert line in fresh and "REQ-001" in fresh and "TEKRARLAMA" in fresh
    assert clean_slate.ban_list([]) == ""


def test_sliced_build_feeds_back_only_unmet_requirements_and_never_gets_worse(tmp_path, monkeypatch):
    import req_checks
    import req_ledger
    import slice_build

    ledger = req_ledger.build(_CONTRACT, _ASK)
    page = "<html><body>{}</body></html>"
    answers = iter(["iskelet", "veri", "etkilesim", "tamam"])
    asked: list[str] = []

    async def generate(system, user):
        asked.append(user)
        return "```html\n" + page.format(next(answers, "kotu")) + "\n```"

    def judge(ws_dir, wanted):
        body = (ws_dir / "index.html").read_text(encoding="utf-8")
        good = {"iskelet": 1, "veri": 2, "etkilesim": 3, "tamam": 99}
        count = next((n for word, n in good.items() if word in body), 0)
        return {r.id: (index < count, "" if index < count else "eksik") for index, r in enumerate(wanted)}

    monkeypatch.setattr(req_checks, "evaluate", judge)
    code = asyncio.run(slice_build.build((tmp_path, "istek", "sistem"), ledger, generate, generate))
    assert "tamam" in code and (tmp_path / "index.html").read_text(encoding="utf-8") == code
    first_fix = next(a for a in asked if "karşılanmıyor" in a)
    assert "REQ-001 [" not in first_fix.split("KULLANICI İSTEĞİ")[0], "karşılanmış koşul geri gönderilmez"
    line, unmet = slice_build.summary(tmp_path)
    assert line.startswith("Koşul defteri:") and unmet == []


def test_unmet_requirement_blocks_the_live_proof(tmp_path):
    import done_gate
    import req_ledger
    import slice_build

    ledger = req_ledger.build({"colors": ["#123456"]}, "")
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    line, unmet = slice_build.final(tmp_path, ledger)
    assert "0/1" in line and "REQ-001" in unmet[0]
    status, detail = done_gate.live_proof(tmp_path, [])
    assert status == done_gate.FAILED and "REQ-001" in detail


_SKELETON = """```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/a")
def read_a():
    \"\"\"a döndürür\"\"\"
    raise NotImplementedError


class Store:
    def total(self, values):
        \"\"\"toplam\"\"\"
        raise NotImplementedError
```"""


def test_long_file_is_filled_function_by_function_into_its_own_place():
    import ast

    import chunked_code

    answers = {
        "read_a": ['```python\ndef read_a():\n    return {"a": 1\n```', '```python\n@app.get("/a")\ndef read_a():\n    return {"a": 1}\n```'],
        "Store.total": ["```python\ndef total(self, values):\n    return sum(values)\n```"],
    }

    async def generate(user):
        return _SKELETON if "İSKELET" in user else answers[user.rsplit(": ", 1)[1]].pop(0)

    code, unfilled = asyncio.run(chunked_code.write("iki uç nokta", generate))
    ast.parse(code)
    assert unfilled == [] and "NotImplementedError" not in code
    assert code.count('@app.get("/a")') == 1 and "    def total(self, values):\n        return sum(values)" in code


def test_unfillable_function_is_reported_and_truncation_is_recognised():
    import chunked_code

    async def generate(user):
        return _SKELETON if "İSKELET" in user else "```python\ndef baska():\n    return 1\n```"

    code, unfilled = asyncio.run(chunked_code.write("istek", generate))
    assert unfilled == ["read_a", "Store.total"] and "NotImplementedError" in code
    long_file = "".join(f"def f{i}():\n    return {i}\n\n\n" for i in range(60))
    assert chunked_code.cut_off("a.py", long_file + "def son(:\n") is True
    assert chunked_code.cut_off("a.py", long_file) is False and chunked_code.cut_off("a.js", long_file + "(") is False
    routes = " ".join(f"GET /kaynak{i}" for i in range(8))
    assert chunked_code.wanted("app/main.py", routes) and not chunked_code.wanted("app/main.py", "GET /a")


def test_critic_is_from_another_family_than_the_writer():
    import critic_models

    installed = ["bge-m3:latest", "qwen2.5-coder:7b", "qwen2.5vl:7b", "qwen3.5:9b", "llama3.2:3b", "deepseek-r1:8b"]
    assert critic_models.pick("qwen2.5-coder:7b", installed) == "deepseek-r1:8b"
    assert critic_models.pick("deepseek-r1:8b", installed) == "llama3.2:3b"
    assert critic_models.pick("qwen3.5:9b", ["qwen3.5:9b", "qwen3.5:4b", "bge-m3:latest"]) == "qwen3.5:9b"


def test_selected_filter_button_passes_when_wired_and_fails_when_dead(tmp_path):
    import req_checks
    import req_ledger

    ledger = req_ledger.build({"buttons": [{"label": "Tümü", "behavior": "hepsini gösterir"}]}, "")
    for script, expected in (("document.getElementById('t').addEventListener('click', () => {})", True), ("", False)):
        (tmp_path / "index.html").write_text(f"<!doctype html><button id='t'>Tümü</button><script>{script}</script>", encoding="utf-8")
        passed, detail = req_checks.evaluate(tmp_path, ledger)["REQ-001"]
        if passed is None:
            pytest.skip("tarayıcı çalıştırılamadı")
        assert passed is expected, detail


def test_persistence_asked_in_everyday_words_is_kept():
    import agent_contracts

    async def chat(system, user, schema, num_ctx):
        return '{"persistence": "görevler"}'

    for ask in ("Görevler sayfa yenilenince de kalsın.", "localStorage kullan"):
        assert asyncio.run(agent_contracts.intake(ask, chat)).persistence == "görevler"
    assert asyncio.run(agent_contracts.intake("Bir görev listesi yap", chat)).persistence == ""


def test_regions_are_found_by_class_names_as_well_as_semantic_tags(tmp_path):
    import req_checks
    import req_ledger

    ledger = req_ledger.build({"regions": ["üst bar", "yan menü", "ana alan", "alt bilgi", "istatistik kutusu"]}, "")
    (tmp_path / "index.html").write_text("<!doctype html><meta charset='utf-8'><div class='header'>a</div><div class='sidebar'>b</div><div class='main'>c</div><div class='footer'>d</div>", encoding="utf-8")
    found = req_checks.evaluate(tmp_path, ledger)
    if any(passed is None for passed, _ in found.values()):
        pytest.skip("tarayıcı çalıştırılamadı")
    assert [found[r.id][0] for r in ledger] == [True, True, True, True, False]
