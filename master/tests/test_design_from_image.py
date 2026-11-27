"""Colour measurement, similarity figures and the request built from a screenshot."""

import io

import pytest

import design_from_image as dfi

pytestmark = pytest.mark.unit


def _picture(header="#1e293b", body="#f8fafc", button="#22c55e"):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (400, 300), body)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 400, 60), fill=header)
    draw.rectangle((40, 100, 200, 150), fill=button)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def test_palette_measures_exact_colours_by_area():
    colours = dfi.palette(_picture())
    assert colours[0][0] == "#f8fafc" and {c for c, _ in colours[:3]} == {"#f8fafc", "#1e293b", "#22c55e"}


def test_similarity_separates_the_same_page_from_a_different_one():
    from PIL import Image, ImageDraw

    other = Image.new("RGB", (400, 300), "#000000")
    ImageDraw.Draw(other).rectangle((300, 0, 400, 300), fill="#ff00ff")
    out = io.BytesIO()
    other.save(out, "PNG")
    assert dfi.similarity(_picture(), _picture()) == (100, 100)
    layout, colour = dfi.similarity(_picture(), out.getvalue())
    assert layout < 40 and colour < 20


def test_request_carries_measured_colours_and_read_texts():
    screen = dfi.Screen(title="Panel", regions=[dfi.Region(name="üst çubuk", elements=["düğme: Kaydet"])], texts=["Kaydet"])
    request = dfi.build_request("koda çevir", [("#f8fafc", 0.7)], screen)
    assert "#f8fafc" in request and '"Kaydet"' in request and "tek HTML" in request


@pytest.mark.parametrize(("prompt", "name", "wanted"), [
    ("bunu koda çevir", "a.png", True), ("bu tasarımı yap", "a.jpg", True), ("bu görselde ne var", "a.png", False), ("koda çevir", "a.pdf", False),
])
def test_trigger(prompt, name, wanted):
    assert dfi.wants_code(prompt, name) == wanted


def test_header_strip_and_button_are_located():
    png = _picture()
    colours = dfi.palette(png)
    strips = dfi.bands(png)
    assert strips[0][2] == "#1e293b" and strips[0][1] == 20 and strips[-1][2] == "#f8fafc"
    button = next(b for b in dfi.blocks(png, colours) if b["colour"] == "#22c55e")
    assert button["x"] == 10 and 32 <= button["y"] <= 34 and 40 <= button["w"] <= 41
