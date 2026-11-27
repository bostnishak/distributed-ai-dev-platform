"""Citation gate and action policy."""

import asyncio

import pytest

import policy
import research

pytestmark = pytest.mark.unit
_PAGE = "Python 3.13 was released on October 7, 2024. It adds an experimental free-threaded build mode."


def test_only_literal_quotes_with_their_numbers_survive():
    raw = [
        research.RawClaim(claim="Python 3.13, 7 Ekim 2024'te çıktı", quote="Python 3.13 was released on October 7, 2024."),
        research.RawClaim(claim="Uydurma alıntı", quote="Python 3.13 doubles the speed of every program."),
        research.RawClaim(claim="Python 3.13 yüzde 40 hızlı", quote="It adds an experimental free-threaded build mode."),
    ]
    assert [c.quote for c in research.verified(raw, _PAGE)] == [raw[0].quote]


def test_report_drops_unbacked_statements_and_lists_sources_itself():
    claims = {1: research.Claim(1, "c", "Python 3.13 was released on October 7, 2024.", "https://example.org/a", "Notes")}
    report = research.Report(
        summary=[research.Point(text="3.13 sürümü 2024'te çıktı", ids=[1]), research.Point(text="Hız %60 arttı", ids=[1]), research.Point(text="Kanıtsız", ids=[9])],
        conflicts=[research.Conflict(ids=[1, 7], explanation="tek kaynaklı çelişki olmaz")],
    )
    text = research.render(report, claims, "python 3.13 ne zaman çıktı", 2)
    assert "2024'te çıktı [1]" in text and "%60" not in text and "Kanıtsız" not in text
    assert "https://example.org/a" in text and "2 cümle silindi" in text and "Çelişen" not in text


def test_whole_run_with_a_fake_model(monkeypatch):
    monkeypatch.setattr(research.research_context, "web_enabled", lambda: True)
    monkeypatch.setattr(research.research_context, "web_search", lambda q, limit=6: [{"url": "https://example.org/a", "title": "Notes"}])
    monkeypatch.setattr(research, "read_page", lambda url: _PAGE * 4)

    async def chat(system, user, schema):
        if "alt sorguya" in system:
            return '{"queries": ["python 3.13 release"]}'
        if "SAYFA METNİ" in user:
            return '{"claims": [{"claim": "3.13, 2024 çıkışlı", "quote": "Python 3.13 was released on October 7, 2024."}]}'
        return '{"summary": [{"text": "2024 yılında çıktı", "ids": [1]}]}'

    async def collect():
        return [item async for item in research.investigate("derin araştır: python 3.13", chat)]

    events = asyncio.run(collect())
    assert events[-1][0] == "report" and "2024 yılında çıktı [1]" in events[-1][1]


def test_trigger_words():
    assert research.wants_research("Katı hal pillerini derinlemesine araştır")
    assert not research.wants_research("bu kodu araştırıp düzelt")


def test_secrets_never_leave():
    key = "sk-" + "a" * 24
    assert not policy.check("web_search", payload=f"neden {key} çalışmıyor", approved=True).allowed


def test_outside_content_lowers_privileges():
    run = policy.Context()
    run.require("mcp_call")
    run.read_external()
    with pytest.raises(policy.PolicyError):
        run.require("mcp_call")
    run.require("mcp_call", approved=True)
    run.require("web_search", payload="hava durumu")


def test_irreversible_actions_always_ask():
    decision = policy.check("browser_submit")
    assert not decision.allowed and decision.needs_approval
    assert policy.check("browser_submit", approved=True).allowed
