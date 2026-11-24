"""The chat prompt must never contain invented data: no sample financials, no analysis of nothing."""

import asyncio
import io

import pytest
from starlette.datastructures import Headers, UploadFile

import assistant
import config
import hybrid_graph_rag

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolated_chat(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    async def no_classifier(_prompt):
        return "genel", False

    monkeypatch.setattr(assistant, "classify_and_moderate", no_classifier)


def _prepare(prompt, file=None):
    return asyncio.run(assistant._prepare_chat_request(prompt, file))[0]


def _text_upload(name, text):
    return UploadFile(
        file=io.BytesIO(text.encode("utf-8")),
        filename=name,
        headers=Headers({"content-type": "text/plain"}),
    )


def test_valuation_request_without_data_asks_for_inputs_instead_of_sample_numbers():
    prompt = _prepare("şirketim için dcf değerleme yap")
    assert "gerçek finansal veri vermedi" in prompt
    assert "Firma Değeri" not in prompt
    assert "10,000,000" not in prompt


def test_contract_keyword_without_a_document_runs_no_analysis():
    prompt = _prepare("sözleşme risk analizi yap")
    assert "Hukuki Sözleşme Risk Motoru" not in prompt


def test_contract_keyword_with_a_document_still_runs_the_analysis():
    contract = _text_upload(
        "sozlesme.txt",
        "Taraflardan biri sebep göstermeksizin tek taraflı fesih hakkına sahiptir. Cezai şart bedelin %50'sidir.",
    )
    prompt = _prepare("bu sözleşme risk analizi yap", contract)
    assert "Hukuki Sözleşme Risk Motoru" in prompt


def _index_gasket_doc():
    rag = hybrid_graph_rag.HybridGraphRAG()
    rag.add_document(
        "zkx", "Conta standardı", "ZKX-9000 contası için sıkma torku 14 Nm olmalıdır.", extract_graph=False
    )


def test_indexed_document_reaches_the_chat_prompt():
    _index_gasket_doc()
    prompt = _prepare("ZKX-9000 conta sıkma torku nedir")
    assert "[GraphRAG]" in prompt
    assert "14 Nm" in prompt


def test_unrelated_question_gets_no_retrieved_context():
    _index_gasket_doc()
    prompt = _prepare("yarın hava nasıl olacak")
    assert "[GraphRAG]" not in prompt
