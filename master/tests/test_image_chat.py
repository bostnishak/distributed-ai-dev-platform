"""Image chat: follow-up edits reach the image engine; unsupported realism is stated honestly."""

import pytest

import image_chat as ic

pytestmark = pytest.mark.unit

GENERATED = [
    {"role": "user", "text": "bana resim üret"},
    {"role": "assistant", "text": "## Üretilen Görsel Tasarım\n![Üretilen Görsel](/api/assistant/media/img-gen-1.svg)"},
]


def test_followup_after_a_generated_image_is_a_revision():
    assert ic.is_image_revision("hayvanlar olan bir resime çevir gündüz olsun", GENERATED) is True
    assert ic.is_image_revision("kaç yaşındasın", GENERATED) is False
    assert ic.is_image_revision("gündüz olsun", [{"role": "assistant", "text": "merhaba"}]) is False
    assert ic.is_image_revision("gündüz olsun", []) is False


def test_realism_requests_are_detected_and_day_cue_is_found():
    assert ic.photoreal_requested("bana resim üret gerçekçi bir resim olsun") is True
    assert ic.photoreal_requested("minimal bir logo üret") is False
    assert ic.wants_daylight("gündüz olsun") is True


def test_honest_message_names_the_limit_and_offers_alternatives():
    assert "Stable Diffusion" in ic.NO_PHOTOREAL_MSG and "illüstrasyon" in ic.NO_PHOTOREAL_MSG.lower()
    assert "tek tek çizemez" in ic.TEMPLATE_NOTE
