"""Exact answers for counting, sorting and tiny Python expressions: a language model gets these wrong, code does not."""

from __future__ import annotations

import ast
import operator
import re
from typing import Any

_WORD_LETTERS_RE = re.compile(r"[\"'\u201c\u2018`]?([^\s\"'\u201c\u201d\u2018\u2019`]{1,60})[\"'\u201d\u2019`]?\s+(?:kelimesinde|sözcüğünde|kelimesi|sözcüğü)\s+kaç\s+(?:harf|karakter)", re.IGNORECASE)
_WORD_COUNT_RE = re.compile(r"(?:metinde|yazıda|cümlede|paragrafta)\s+kaç\s+(?:kelime|sözcük)|kaç\s+(?:kelime|sözcük)\s+(?:var|içeriyor)", re.IGNORECASE)
_SORT_RE = re.compile(r"sırala|sıralar mısın|sort", re.IGNORECASE)
_DESC_RE = re.compile(r"büyükten\s+küçüğe|azalan|ters\s+sıra|descending", re.IGNORECASE)
_PRINT_RE = re.compile(r"print\((.+)\)\s*(?:çıktısı|ne\s+yazdırır|sonucu|ne\s+verir|nedir|ne\s+olur)", re.IGNORECASE | re.DOTALL)
_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_FUNCS: dict[str, Any] = {"sum": sum, "len": len, "min": min, "max": max, "abs": abs, "round": round, "sorted": sorted, "range": range, "list": list, "str": str, "int": int, "float": float}
_MAX_POW = 10_000


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return -_eval(node.operand) if isinstance(node.op, ast.USub) else _eval(node.operand)
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e) for e in node.elts]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        args = [_eval(a) for a in node.args]
        if node.func.id == "range" and any(abs(a) > _MAX_POW * 100 for a in args):
            raise ValueError("range too large")
        return _FUNCS[node.func.id](*args)
    raise ValueError("unsupported expression")


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def _count_letters(prompt: str) -> str | None:
    m = _WORD_LETTERS_RE.search(prompt)
    if not m:
        return None
    word = m.group(1)
    letters = [c for c in word if c.isalpha()]
    return f"\"{word}\" kelimesinde **{len(letters)}** harf var: " + ", ".join(letters) + "."


def _count_words(prompt: str) -> str | None:
    m = _WORD_COUNT_RE.search(prompt)
    if not m:
        return None
    quoted = re.search(r"[\"“]([^\"“”]+)[\"”]", prompt)
    if quoted and len(quoted.group(1).split()) >= 2:  # the quotes say exactly which text is meant
        return f"Metinde **{len(quoted.group(1).split())}** kelime var."
    body = re.sub(r"\s+(?:bu|şu|metninde|metninin|yazısında|cümlesinde|paragrafında)$", "", prompt[: m.start()].strip()).strip()
    if len(body.split()) < 2:
        body = prompt[m.end():].strip()
    words = body.split()
    return f"Metinde **{len(words)}** kelime var." if len(words) >= 2 else None


def _sort_numbers(prompt: str) -> str | None:
    if not _SORT_RE.search(prompt):
        return None
    nums = [float(x.replace(",", ".")) for x in re.findall(r"-?\d+(?:[.,]\d+)?", prompt)]
    if len(nums) < 2 or len(prompt) > 400:
        return None
    desc = bool(_DESC_RE.search(prompt))
    ordered = sorted(nums, reverse=desc)
    return f"{'Büyükten küçüğe' if desc else 'Küçükten büyüğe'} sıralama: " + ", ".join(_fmt(n) for n in ordered)


def _python_output(prompt: str) -> str | None:
    m = _PRINT_RE.search(prompt)
    if not m or len(prompt) > 300:
        return None
    try:
        value = _eval(ast.parse(m.group(1).strip(), mode="eval").body)
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError, OverflowError, MemoryError):
        return None
    return f"Çıktı: `{value}`"


_PANGRAM_RE = re.compile(r"(?:ığüşöç|\u0131\u011f\u00fc\u015f\u00f6\u00e7|türkçe\s+(?:özel\s+)?harf\w*)[^.?!]{0,60}(?:hepsini|tamamını|tümünü)[^.?!]{0,40}cümle|cümle[^.?!]{0,40}(?:ığüşöç|\u0131\u011f\u00fc\u015f\u00f6\u00e7)", re.IGNORECASE)
PANGRAM = "Pijamalı hasta yağız şoföre çabucak güvendi."


def _turkish_special_letters(prompt: str) -> str | None:
    if not _PANGRAM_RE.search(prompt):
        return None
    return f"{PANGRAM}\n\nBu cümlede ı, ğ, ü, ş, ö ve ç harflerinin hepsi geçiyor."


def answer(prompt: str) -> str | None:
    """Return an exact answer for a counting / sorting / print-expression question, else None."""
    text = (prompt or "").strip()
    for fn in (_python_output, _count_letters, _sort_numbers, _count_words, _turkish_special_letters):
        if (res := fn(text)) is not None:
            return res
    return None
