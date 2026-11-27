"""Numbers computed with NumPy and SciPy instead of by the model: sensitivity analysis, numeric root, minimum,
maximum and definite integral.

  duyarlılık: kâr = (fiyat - maliyet) * adet; fiyat=100; maliyet=60; adet=1000; ±%10
  sayısal integral: exp(-x^2); x=0..1
  sayısal kök: cos(x) - x; x=0..1
  en küçük değer: x^2 - 4x + 7; x=0..10

Only digits, operators, listed functions and the declared names reach the parser.
"""

from __future__ import annotations

import re
from typing import Any

_FUNCTIONS = ("sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "exp", "log", "sqrt", "abs", "pi")
_ASK_RE = re.compile(r"^\s*(?P<what>duyarlılık(?:\s+analizi)?|sayısal\s+integral|sayısal\s+kök|en\s+küçük\s+değer|en\s+büyük\s+değer)\s*:\s*(?P<body>.+)$", re.IGNORECASE | re.DOTALL)
_SWING_RE = re.compile(r"(?:±|\+/-)\s*%\s*(\d{1,2})|(?:±|\+/-)\s*(\d{1,2})\s*%")
_RANGE_RE = re.compile(r"^(?P<name>[^\W\d]\w*)\s*=\s*(?P<low>-?\d+(?:[.,]\d+)?)\s*\.\.\s*(?P<high>-?\d+(?:[.,]\d+)?)$")
_ALLOWED_RE = re.compile(r"[\w\s+\-*/^()]*")


def _number(text: str) -> float:
    return float(text.replace(",", "."))


def compile_expression(text: str, names: list[str]) -> Any:
    """A NumPy function of `names`; ValueError for anything that is not plain arithmetic over them."""
    import sympy
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    if len(text) > 200 or not _ALLOWED_RE.fullmatch(re.sub(r"(?<=\d)[.,](?=\d)", "", text)) or re.search(r"\^\s*\d{4,}|\*\*\s*\d{4,}", text):
        raise ValueError("ifade yalnız sayı, işlem, parantez ve tanımlı adlar içerebilir")
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    aliases = {name: f"v{i}_" for i, name in enumerate(names)}
    for word in set(re.findall(r"[^\W\d]\w*", text)):
        if word not in aliases and word.lower() not in _FUNCTIONS:
            raise ValueError(f"tanımsız ad: {word}")
    for name, alias in sorted(aliases.items(), key=lambda item: -len(item[0])):
        text = re.sub(rf"(?<![^\W\d]){re.escape(name)}(?!\w)", alias, text)
    symbols = [sympy.Symbol(alias) for alias in aliases.values()]
    transforms = (*standard_transformations, implicit_multiplication_application, convert_xor)
    expression = parse_expr(text, transformations=transforms, local_dict={**{str(s): s for s in symbols}, "pi": sympy.pi, "abs": sympy.Abs})
    return sympy.lambdify(symbols, expression, modules=["numpy"])


def sensitivity(body: str) -> str:
    import numpy as np

    swing_match = _SWING_RE.search(body)
    swing = int(swing_match[1] or swing_match[2]) / 100 if swing_match else 0.10
    parts = [p.strip() for p in re.split(r"[;\n]", _SWING_RE.sub("", body)) if p.strip()]
    if len(parts) < 2 or "=" not in parts[0]:
        raise ValueError("biçim: sonuç = ifade; ad=değer; ...")
    result_name, formula = (side.strip() for side in parts[0].split("=", 1))
    values = {name.strip(): _number(value.strip()) for name, value in (p.split("=", 1) for p in parts[1:] if "=" in p)}
    if not values:
        raise ValueError("değişken değerleri yok")
    names = list(values)
    function = compile_expression(formula, names)
    base_point = np.array([values[n] for n in names], dtype=float)
    base = float(function(*base_point))
    rows = []
    for index, name in enumerate(names):
        points = [base_point.copy(), base_point.copy()]
        points[0][index] *= 1 - swing
        points[1][index] *= 1 + swing
        low, high = (float(function(*p)) for p in points)
        elasticity = ((high - low) / base) / (2 * swing) if base else float("nan")
        rows.append((abs(high - low), name, low, high, elasticity))
    rows.sort(reverse=True)
    percent = f"%{swing * 100:.0f}"
    table = "\n".join(f"| {name} | {low:,.2f} | {high:,.2f} | {span:,.2f} | {'-' if np.isnan(e) else f'{e:.2f}'} |" for span, name, low, high, e in rows)
    return (f"**{result_name} (temel durum): {base:,.2f}**\n\n| Değişken | -{percent} | +{percent} | Fark | Esneklik |\n|---|---|---|---|---|\n{table}\n\n"
            f"En çok etkileyen: **{rows[0][1]}**. Her satırda yalnız o değişken değiştirildi, ötekiler sabit.")


def numeric(what: str, body: str) -> str:
    from scipy import integrate, optimize

    parts = [p.strip() for p in body.split(";") if p.strip()]
    span = _RANGE_RE.match(parts[1]) if len(parts) == 2 else None
    if span is None:
        raise ValueError("biçim: ifade; x=alt..üst")
    low, high = _number(span["low"]), _number(span["high"])
    if not low < high:
        raise ValueError("alt sınır üst sınırdan küçük olmalı")
    function = compile_expression(parts[0], [span["name"]])
    name = span["name"]
    if "integral" in what:
        value, error = integrate.quad(function, low, high, limit=200)
        return f"**∫ = {value:.10g}** ({name}: {low:g} → {high:g}); tahmini hata {error:.2g}"
    if "kök" in what:
        if function(low) * function(high) > 0:
            raise ValueError("aralığın iki ucunda işaret aynı: bu aralıkta kök garanti edilemiyor, aralığı değiştir")
        root = optimize.brentq(function, low, high)
        return f"**{name} ≈ {root:.10g}** (ifade orada {function(root):.2g})"
    sign = -1 if "büyük" in what else 1
    found = optimize.minimize_scalar(lambda x: sign * function(x), bounds=(low, high), method="bounded", options={"xatol": 1e-10})
    point, value = min(((found.x, found.fun), (low, sign * function(low)), (high, sign * function(high))), key=lambda p: p[1])
    return f"**{name} ≈ {point:.8g}**, değer {sign * value:.10g} ({low:g}..{high:g} aralığında). Birden çok tepe varsa aralığı daraltıp doğrula."


def answer(prompt: str) -> str:
    """The reply for a numeric request; "" for everything else."""
    asked = _ASK_RE.match(prompt)
    if asked is None or len(prompt) > 600:
        return ""
    what = " ".join(asked["what"].lower().split())
    try:
        result = sensitivity(asked["body"]) if what.startswith("duyarlılık") else numeric(what, asked["body"])
    except ImportError:
        return "NumPy/SciPy kurulu değil."
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError, OverflowError, RecursionError, NameError) as exc:
        return f"Hesaplanamadı: {exc}"
    return f"{result}\n\n_NumPy/SciPy ile hesaplandı; model tahmini değildir._"
