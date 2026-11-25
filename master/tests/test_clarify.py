"""Open-ended requests are answered with a question; specific ones go straight through."""

import json

import pytest

import clarify

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "prompt",
    ["bir logo yap", "bana bir web sitesi yap", "rapor hazırla", "bir uygulama yaz", "kod yaz", "görsel üret"],
)
def test_vague_creation_requests_get_a_question(prompt):
    out = clarify.clarifying_question(prompt)
    assert out and clarify.CLARIFY_MARKER in out


@pytest.mark.parametrize(
    "prompt",
    [
        "bana bir fotoğraf üret güneş olsun dağ olsun koyunlar olsun",
        "Aylık bütçe takibi için formüllü bir excel tablosu hazırla",
        "Python ile iki sayının ebobunu bulan bir fonksiyon yaz",
        "2+2 kaçtır?",
        "Türkiye'nin başkenti neresidir",
    ],
)
def test_specific_or_plain_questions_go_straight_through(prompt):
    assert clarify.clarifying_question(prompt) is None


def test_attachment_skips_and_followups_lean_on_history():
    assert clarify.clarifying_question("bir logo yap", has_file=True) is None
    hist = json.dumps([{"role": "user", "text": "merhaba"}])
    assert clarify.clarifying_question("bir logo yap", history=hist)  # still vague in an ongoing chat
    assert clarify.clarifying_question("bir logo daha yap", history=hist) is None  # follow-up: uses the conversation


def test_answer_after_our_question_is_not_asked_again():
    hist = json.dumps([{"role": "assistant", "text": f"{clarify.CLARIFY_MARKER} (görsel isteği)"}])
    assert clarify.clarifying_question("logo yap", history=hist) is None


def test_dangling_reference_in_a_new_chat_asks_what_is_meant():
    assert "kastettiğini" in clarify.clarifying_question("bunu düzelt")
    assert clarify.clarifying_question("bunu düzelt", history=json.dumps([{"role": "user", "text": "x"}])) is None
