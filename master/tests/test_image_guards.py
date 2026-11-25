"""English drawing requests are image requests; explicit subjects the engine cannot draw and sexual content are declined honestly."""

import pytest

import image_chat as ic
import multimodal_studio as mms

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("p", ["draw a red sunset over the sea", "bir kedi çiz", "dağ manzarası çiz"])
def test_drawing_requests_detected(p):
    assert mms.is_image_generation_request(p, False)


@pytest.mark.parametrize("p", ["Python ile ağaç çizen kod yaz", "bir tablo çiz", "grafik çiz"])
def test_code_or_table_drawing_is_not_an_image(p):
    assert not mms.is_image_generation_request(p, False)


def test_subjects_and_nsfw():
    assert ic.unsupported_subject("bir kedi çiz") == "kedi"
    assert ic.unsupported_subject("dağ manzarası çiz") is None
    assert ic.unsupported_subject("kedi logosu tasarla") is None  # logos are drawn from the brand name, not the animal
    assert ic.nsfw_requested("çıplak bir kadın resmi çiz")
    assert not ic.nsfw_requested("gün batımı manzarası çiz")
