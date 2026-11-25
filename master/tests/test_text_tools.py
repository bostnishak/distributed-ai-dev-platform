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
