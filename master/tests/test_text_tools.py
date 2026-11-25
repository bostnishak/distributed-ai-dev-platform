"""Counting, sorting and tiny Python expressions are answered exactly, without a model."""

import pytest

from text_tools import answer

pytestmark = pytest.mark.unit


def test_letters_in_word():
    assert "**8**" in answer('"kardelen" kelimesinde kaç harf var?')


def test_sort_numbers_both_directions():
    assert answer("5, 3, 9, 1, 7 sayılarını büyükten küçüğe sırala").endswith("9, 7, 5, 3, 1")
    assert answer("5, 3, 9, 1 sayılarını sırala").endswith("1, 3, 5, 9")


def test_print_expression():
    assert answer("print(sum(range(101))) çıktısı ne?") == "Çıktı: `5050`"
    assert answer("print(2**10) çıktısı nedir") == "Çıktı: `1024`"


def test_words_in_pasted_text():
    assert "**5**" in answer("bir iki üç dört beş bu metinde kaç kelime var?")


@pytest.mark.parametrize("p", ["print(open('x').read()) çıktısı ne?", "print(__import__('os')) çıktısı", "print(9**9**9) çıktısı", "Python nedir?", "Ankara'nın nüfusu kaç"])
def test_unsafe_or_unrelated_returns_none(p):
    assert answer(p) is None


@pytest.mark.parametrize("prompt,expected", [
    ("Üç kutu var: biri sadece elma, biri sadece portakal, biri karışık içeriyor. Üçünün etiketi de yanlış. Karışık etiketli kutudan çekersem nasıl bulurum?", True),
    ("İki zar atılıyor. Toplamın 9 olma olasılığı nedir?", True),
    ("5 kişi bir işi 12 günde bitiriyor, 8 kişi aynı işi kaç günde bitirir?", True),
    ("bana mantıklı bir isim öner lütfen çok güzel olsun", False),
    ("Python ile olasılık hesaplayan kod yaz lütfen bana", False),
])
def test_puzzle_detection_is_precise(prompt, expected):
    import reasoning_mode

    assert reasoning_mode.needs_thinking(prompt) is expected
