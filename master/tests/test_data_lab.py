"""CSV questions run as read-only SQL."""

import asyncio

import pytest

import data_lab

pytestmark = pytest.mark.unit
_CSV = "ay,şehir,satış\nOcak,Ankara,100\nOcak,İzmir,250\nŞubat,Ankara,400\n"


def test_select_computes_the_real_total():
    pytest.importorskip("duckdb")
    assert data_lab.run_select(_CSV, 'SELECT sum("satış") AS toplam FROM veri')[1] == [(750,)]


@pytest.mark.parametrize("sql", ["DROP TABLE veri", "SELECT 1; DELETE FROM veri", "SELECT * FROM read_text('C:/Windows/win.ini')", "COPY veri TO 'x.csv'"])
def test_everything_but_a_plain_select_is_refused(sql):
    with pytest.raises(ValueError, match="SELECT"):
        data_lab.run_select(_CSV, sql)


def test_a_failing_query_is_retried_with_the_error():
    pytest.importorskip("duckdb")
    asked = []

    async def chat(system, user, schema):
        asked.append(user)
        return '{"sql": "SELECT yok FROM veri"}' if len(asked) == 1 else '{"sql": "SELECT count(*) FROM veri"}'

    out = asyncio.run(data_lab.verified_facts("kaç satır var?", "s.csv", _CSV, chat))
    assert "hata verdi" in asked[1] and "DOĞRULANMIŞ HESAP" in out and "\n3\n" in out
