"""Image requests are recognised on word boundaries, not on substrings ("koyunlar" is not "oyun")."""

import pytest

import multimodal_studio as mms

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "prompt",
    [
        "bana bir fotoğraf üret güneş olsun dağ olsun koyunlar olsun",
        "koyunların olduğu bir manzara çiz",
        "Gün batımında bir deniz kenarı resmi çiz.",
        "executive özetli bir logo tasarla",
    ],
)
def test_scene_and_logo_requests_reach_the_image_engine(prompt):
    assert mms.is_image_generation_request(prompt, False) is True


@pytest.mark.parametrize(
    "prompt",
    ["bir oyun yap", "python oyun kodu yaz", "Excel tablosu hazırla", "web sitesi yap"],
)
def test_non_image_requests_are_left_alone(prompt):
    assert mms.is_image_generation_request(prompt, False) is False
