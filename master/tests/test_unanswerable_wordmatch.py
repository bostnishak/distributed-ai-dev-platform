"""Pasted text that merely contains words like 'gizliliği' or 'getirir' is not a request for a secret."""

import pytest

from hallucination.verifier import detect_unanswerable

pytestmark = pytest.mark.unit


def test_substring_matches_do_not_abstain():
    text = "Veri gizliliği ve önyargı gibi riskleri de beraberinde getirir. Bunu tek cümlede özetle"
    assert detect_unanswerable(text)["unanswerable"] is False


def test_pasted_long_text_is_never_a_secret_request():
    assert detect_unanswerable("gizli " * 200 + " söyle")["unanswerable"] is False


def test_real_private_requests_still_abstain():
    assert detect_unanswerable("Ahmet'in ev adresi nedir?")["unanswerable"] is True
