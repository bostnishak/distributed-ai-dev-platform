"""Exploratory analysis and an honest predictive model for an uploaded table, computed in code.

The profile (types, missing values, statistics, correlations, outliers) and a cross-validated model are measured, not
written by a language model. The score is always shown next to the trivial baseline, identifier columns are dropped,
and a column that gives the answer away is reported as leakage instead of celebrated.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import automl_studio
import extract
import turkish

_log = logging.getLogger(__name__)
_EDA_RE = re.compile(r"keşif\s+analiz|veri\s+analiz\w*|analiz\s+raporu|\beda\b|veriyi\s+incele|veri\s+profil|tahmin\s+modeli|tahmin\s+et|predict\b|profile\s+this\s+data", re.IGNORECASE)
_MODEL_RE = re.compile(r"tahmin\s+modeli|tahmin\s+et|predict\b|model\s+kur", re.IGNORECASE)
_MAX_ROWS = 50_000


def rows_of(text: str) -> list[dict[str, str]]:
    sample = text[:4000]
    delimiter = max((",", ";", "\t", "|"), key=sample.count)
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))[:_MAX_ROWS]


def target_of(prompt: str, columns: list[str]) -> str:
    asked = turkish.lower(prompt)  # "İl" must match "il": plain casefold keeps a dot on İ and never does
    named = [c for c in columns if c and re.search(rf"(?<![\w]){re.escape(turkish.lower(c))}(?![a-zçğıöşü0-9])", asked)]
    return max(named, key=len) if named else ""


def _number(value: str) -> float | None:
    try:
        return float(str(value).replace(",", ".")) if str(value).strip() else None
    except ValueError:
        return None


def _encode(rows: list[dict[str, str]], name: str) -> tuple[list, bool] | None:
    """(numbers for the model, was numeric); None for identifier and free-text columns."""
    raw = [str(r.get(name, "")).strip() for r in rows]
    numbers = [_number(v) for v in raw]
    known = sorted(n for n in numbers if n is not None)
    numeric = len(known) >= 0.9 * len(rows)
    if len(set(raw)) == len(rows) and (not numeric or re.search(r"(?:^|_)id$|^id|no$", name, re.IGNORECASE)):
        return None
    if numeric:
        return [n if n is not None else known[len(known) // 2] for n in numbers], True
    if len(set(raw)) > 30:
        return None
    codes = {v: i for i, v in enumerate(sorted(set(raw)))}
    return [codes[v] for v in raw], False


def _leaks(column: list, numeric: bool, y: list, regression: bool) -> bool:
    """A column from which the answer can simply be read off."""
    if regression:
        return numeric and all(abs(a - b) < 1e-9 for a, b in zip(column, y, strict=True))
    groups: dict[object, set] = {}
    for value, answer in zip(column, y, strict=True):
        groups.setdefault(value, set()).add(answer)
    return 1 < len(groups) <= len(set(y)) and all(len(g) == 1 for g in groups.values())


def _features(rows: list[dict[str, str]], target: str, y: list, regression: bool) -> tuple[dict[str, list], list[str], list[str]]:
    """(usable columns, dropped names, leaking names)."""
    used: dict[str, list] = {}
    dropped: list[str] = []
    leaking: list[str] = []
    for name in (c for c in rows[0] if c != target):
        encoded = _encode(rows, name)
        if encoded is None:
            dropped.append(name)
        elif _leaks(encoded[0], encoded[1], y, regression):
            leaking.append(name)
        else:
            used[name] = encoded[0]
    return used, dropped, leaking


def _fit(features: dict[str, list], y: list, regression: bool) -> list[str]:
    """Cross-validated score against the trivial baseline, and the most useful columns when the model beats it."""
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score

    columns = list(features)
    matrix = [list(row) for row in zip(*features.values(), strict=True)]
    if regression:
        model, folds, scoring, label = RandomForestRegressor(n_estimators=120, random_state=7), KFold(5, shuffle=True, random_state=7), "r2", "R² (1 kusursuz, 0 ortalamayı söylemekle aynı)"
        baseline = 0.0
    else:
        model, folds, scoring, label = RandomForestClassifier(n_estimators=120, random_state=7), StratifiedKFold(5, shuffle=True, random_state=7), "accuracy", "doğruluk"
        baseline = max(y.count(v) for v in set(y)) / len(y)
    scores = cross_val_score(model, matrix, y, cv=folds, scoring=scoring)
    mean, spread = float(scores.mean()), float(scores.std())
    lines = [f"5 katlı çapraz doğrulama {label}: **{mean:.3f}** ± {spread:.3f} (hiçbir şey öğrenmeden: {baseline:.3f})"]
    if mean <= baseline + max(spread, 0.02):
        return [*lines, "**Sonuç: model, en basit tahminden anlamlı ölçüde iyi değil.** Bu sütunlarla hedef tahmin edilemiyor görünüyor."]
    importance = permutation_importance(model.fit(matrix, y), matrix, y, n_repeats=5, random_state=7, scoring=scoring).importances_mean
    order = sorted(range(len(columns)), key=lambda i: -importance[i])[:5]
    return [*lines, "En etkili sütunlar: " + ", ".join(f"{columns[i]} ({importance[i]:.3f})" for i in order) + " — ilişki gösterir, nedensellik kanıtlamaz."]


def model_report(rows: list[dict[str, str]], target: str) -> list[str]:
    """Lines describing a 5-fold cross-validated model for `target`, or why none was built."""
    rows = [r for r in rows if str(r.get(target, "")).strip()]
    if len(rows) < 30:
        return [f"`{target}` için yalnız {len(rows)} dolu satır var; güvenilir bir model için en az 30 gerekir. Model kurulmadı."]
    values = [str(r[target]).strip() for r in rows]
    regression = all(_number(v) is not None for v in values) and len(set(values)) > 10
    y = [_number(v) for v in values] if regression else values
    if not regression and (len(set(values)) < 2 or min(values.count(v) for v in set(values)) < 5):
        return [f"`{target}` sınıflarından en az biri 5'ten az örnek içeriyor ya da tek sınıf var; model kurulmadı."]
    features, dropped, leaking = _features(rows, target, y, regression)
    if not features:
        return ["Tahminde kullanılabilecek sütun kalmadı (kimlik ve sızıntı sütunları çıkarıldı)."]
    lines = [f"Hedef `{target}` ({'sayı' if regression else 'sınıf'}), {len(rows)} satır, {len(features)} girdi sütunu.", *_fit(features, y, regression)]
    if leaking:
        lines.append(f"UYARI (sızıntı): {', '.join(leaking)} hedefi bire bir veriyor; modele katılmadı.")
    if dropped:
        lines.append(f"Kimlik ya da serbest metin sütunları çıkarıldı: {', '.join(dropped)}.")
    return lines


def report(text: str, prompt: str) -> str:
    rows = rows_of(text)
    if len(rows) < 2:
        return "Dosyada analiz edilecek tablo bulunamadı."
    profile = automl_studio.profile_dataset(rows)
    out = [f"## Veri profili\n{profile['row_count']} satır, {profile['column_count']} sütun."]
    missing = {c: n for c, n in profile["missing_counts"].items() if n}
    out.append("Eksik değerler: " + (", ".join(f"{c}: {n}" for c, n in missing.items()) if missing else "yok") + ".")
    if profile["numeric_columns"]:
        out += ["", "| Sütun | ortalama | en küçük | en büyük | std |", "|---|---|---|---|---|"]
        for name in profile["numeric_columns"][:12]:
            stats = profile["numeric_stats"][name]
            out.append(f"| {name} | {stats.get('mean', 0):.4g} | {stats.get('min', 0):.4g} | {stats.get('max', 0):.4g} | {stats.get('std', 0):.4g} |")
    pairs = [(a, b, r) for i, a in enumerate(profile["numeric_columns"]) for b in profile["numeric_columns"][i + 1 :]
             if (r := profile["correlation_matrix"].get(a, {}).get(b)) is not None and abs(r) >= 0.5]
    if pairs:
        out += ["", "Güçlü ilişkiler: " + "; ".join(f"{a} / {b}: r={r:.2f}" for a, b, r in sorted(pairs, key=lambda p: -abs(p[2]))[:5])]
    if profile["anomalies"]:
        out += ["", f"Aykırı değer içeren {len(profile['anomalies'])} satır var; ilki: satır {profile['anomalies'][0]['row_index'] + 2} ({'; '.join(profile['anomalies'][0]['reasons'][:2])})."]
    if _MODEL_RE.search(prompt):
        target = target_of(prompt, list(rows[0]))
        out += ["", "## Tahmin modeli"]
        out += model_report(rows, target) if target else [f"Hangi sütunun tahmin edileceğini yazman gerekiyor. Sütunlar: {', '.join(rows[0])}"]
    return "\n".join([*out, "", "_Bütün rakamlar dosyadan kodla hesaplandı; dil modeli kullanılmadı._"])


def fastpath(prompt: str, file: UploadFile) -> StreamingResponse | None:
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".tsv")) or not _EDA_RE.search(prompt):
        return None
    raw = file.file.read(20_000_000)
    file.file.seek(0)
    text = raw.decode("utf-8-sig", "replace")

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def gen():
        yield sse({"type": "status", "message": "Veri analiz ediliyor..."})
        try:
            yield sse({"type": "token", "content": report(text, prompt)})
        except (ImportError, ValueError, KeyError, TypeError, csv.Error, extract.UnsupportedFileError) as exc:
            _log.warning("eda failed: %r", exc)
            yield sse({"type": "error", "content": f"Analiz yapılamadı: {exc}"})
        yield sse({"type": "done", "model": "eda", "task_type": "analiz"})

    return StreamingResponse(gen(), media_type="text/event-stream")
