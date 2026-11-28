import asyncio

import pytest

import research

pytestmark = pytest.mark.unit


def test_empty_summary_from_the_model_is_replaced_by_the_cited_claims():
    """The failure the certification found: valid JSON with no statements left a report without citations."""
    claims = {1: research.Claim(1, "Readers do not block writers.", "readers and writers can run at the same time", "https://a.example/x", "A")}

    async def chat(_system, _user, _schema):
        return '{"summary": [], "details": [], "open_questions": ["q"]}'

    report = asyncio.run(research._write_report("WAL?", claims, chat))
    assert [p.ids for p in report.summary] == [[1]] and report.open_questions == ["q"]
