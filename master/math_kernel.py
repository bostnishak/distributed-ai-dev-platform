"""Symbolic maths answered by SymPy, not by the model: derivative, integral, solve, factor, expand, simplify, limit.

Only a request made of one recognised operation word and one plain expression is taken; anything else goes to the
model. The expression is checked character by character and name by name before SymPy sees it.
"""

from __future__ import annotations

import re

_OPERATIONS = (
    ("derivative", re.compile(r"\b(?:türevini?\s*(?:al|hesapla|bul)?|türevi\s*(?:nedir|ne)|derivative of|differentiate)", re.IGNORECASE)),
    ("integral", re.compile(r"\b(?:integralini?\s*(?:al|hesapla|bul)?|integrali\s*(?:nedir|ne)|integral of|integrate)", re.IGNORECASE)),
    ("factor", re.compile(r"\b(?:çarpanlarına ayır\w*|factor(?:ize)?\b)", re.IGNORECASE)),
    ("expand", re.compile(r"\b(?:parantezleri aç\w*|expand\b)", re.IGNORECASE)),
    ("simplify", re.compile(r"\b(?:sadeleştir\w*|simplify\b)", re.IGNORECASE)),
    ("solve", re.compile(r"\b(?:denklemini?\s*çöz\w*|çözün|çöz\b|köklerini bul\w*|solve\b)", re.IGNORECASE)),
)
_FUNCTIONS = {"sin", "cos", "tan", "cot", "asin", "acos", "atan", "sinh", "cosh", "tanh", "exp", "log", "ln", "sqrt", "pi", "abs"}
_EXPR_RE = re.compile(r"[0-9a-z\s+\-*/^().=,²³]+", re.IGNORECASE)
_FILLER_RE = re.compile(
    r"\b(?:ifadesinin|ifadesini|fonksiyonunun|fonksiyonunu|denklemi|denklemini|ifadesi|şu|bu|lütfen|nin|nın|nun|nün|göre|değişkenine|the|please|with respect to x|for x)\b|[?!:;'\u2019]|f\(x\)\s*=",
    re.IGNORECASE,
)
_LIMIT = 200


def parse(prompt: str) -> tuple[str, str] | None:
    """(operation, expression) when the whole message is a single maths request."""
    if len(prompt) > _LIMIT:
        return None
    for name, pattern in _OPERATIONS:
        if not pattern.search(prompt):
            continue
        text = _FILLER_RE.sub(" ", pattern.sub(" ", prompt)).strip().strip(".,").strip()
        text = text.replace("²", "^2").replace("³", "^3")
        if not text or not _EXPR_RE.fullmatch(text):
            return None
        words = re.findall(r"[a-z]{2,}", text, re.IGNORECASE)
        if any(w.lower() not in _FUNCTIONS for w in words) or not re.search(r"[a-z]", text, re.IGNORECASE):
            return None
        if re.search(r"\^\s*\d{4,}|\d{25,}|\^[^+\-*/)]*\^", text):
            return None  # towers and huge powers would run for a very long time
        return name, text
    return None


def _expression(text: str):
    from sympy import E, pi
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    transforms = (*standard_transformations, implicit_multiplication_application, convert_xor)
    return parse_expr(text, transformations=transforms, local_dict={"e": E, "pi": pi})


def _show(value) -> str:
    return str(value).replace("**", "^")


def solve_text(operation: str, text: str) -> str:
    """The answer as chat markdown; '' when SymPy cannot do it (the model then answers instead)."""
    from sympy import Eq, Symbol, diff, expand, factor, integrate, simplify, solve

    try:
        if "=" in text:
            left, right = text.split("=", 1)
            expr = _expression(left) - _expression(right or "0")
        else:
            expr = _expression(text)
        symbols = sorted(expr.free_symbols, key=str)
        x = next((s for s in symbols if s.name == "x"), symbols[0] if symbols else Symbol("x"))
        if operation == "derivative":
            return f"**Türev** ({x} değişkenine göre): `{_show(simplify(diff(expr, x)))}`"
        if operation == "integral":
            result = integrate(expr, x)
            if result.has(type(integrate(Symbol("q") ** Symbol("q"), Symbol("q")))):
                return ""
            checked = simplify(diff(result, x) - expr) == 0
            return f"**İntegral** ({x} değişkenine göre): `{_show(result)} + C`" + ("\n\nSağlama: türevi alınınca başlangıç ifadesi elde ediliyor." if checked else "")
        if operation == "solve":
            roots = solve(Eq(expr, 0), x)
            if not roots:
                return f"`{_show(expr)} = 0` denkleminin çözümü yok."
            lines = [f"- {x} = `{_show(r)}`" + (f" ≈ {float(r):.6g}" if r.is_real and not r.is_Integer else "") for r in roots]
            checked = all(simplify(expr.subs(x, r)) == 0 for r in roots)
            return "**Çözümler:**\n" + "\n".join(lines) + ("\n\nSağlama: her kök denklemde yerine konunca 0 veriyor." if checked else "")
        action = {"factor": ("Çarpanlar", factor), "expand": ("Açılım", expand), "simplify": ("Sade hali", simplify)}[operation]
        return f"**{action[0]}:** `{_show(action[1](expr))}`"
    except (SyntaxError, TypeError, ValueError, AttributeError, NotImplementedError, ZeroDivisionError, RecursionError):
        return ""


_POWER_RE = re.compile(
    r"^\s*(?P<n>\d{1,12}(?:[.,]\d{1,6})?)\s*(?:['\u2019]?\s*(?:n?[iıuü]n)|\s+sayısının)?\s+(?P<op>karekökü|küpkökü|küp\s+kökü|kare\s+kökü|karesi|küpü)\s*(?:kaçtır|kaç|nedir)?\s*\??\s*$", re.IGNORECASE)


def number_question(prompt: str) -> str:
    """"144'ün karekökü kaç?" computed here: small models mix up the root and the square when they word it."""
    match = _POWER_RE.match(prompt)
    if not match:
        return ""
    from sympy import Rational, cbrt, sqrt

    written, op = match["n"], " ".join(match["op"].casefold().split())
    value = Rational(written.replace(",", "."))
    action = {"karekökü": sqrt, "kare kökü": sqrt, "küpkökü": cbrt, "küp kökü": cbrt, "karesi": lambda v: v**2, "küpü": lambda v: v**3}[op]
    result = action(value)
    shown = str(result) if result.is_Integer else ("" if result.is_Rational else "≈ ") + f"{float(result):.10g}".replace(".", ",")
    return f"{written} sayısının {op}: **{shown}**"


def answer(prompt: str) -> str:
    """Complete reply for a maths request, '' for everything else."""
    if direct := number_question(prompt):
        return direct
    parsed = parse(prompt)
    if not parsed:
        return ""
    try:
        result = solve_text(*parsed)
    except ImportError:
        return ""
    return f"{result}\n\n_SymPy ile hesaplandı; model tahmini değildir._" if result else ""
