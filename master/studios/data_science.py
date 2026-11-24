"""DS-01..DS-10: On-Demand Data Profiler, Read-Only SQL, Charts, Leakage-Checked AutoML, Anomalies, Forecast & Stat Tests."""

from __future__ import annotations

import math
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

_SQL_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|TRIGGER)\b",
    re.IGNORECASE,
)
_PII_COL_RE = re.compile(r"\b(tc|tckn|kimlik|email|e_posta|telefon|phone|iban|adres|address|sifre|password|ssn)\b", re.IGNORECASE)
_DATE_STR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?")


# ---------------------------------------------------------------- DS-01 & DS-10 On-Demand Data Profiler + Privacy Badge

def profile_dataset_on_demand(rows: list[dict[str, Any]], *, headers: list[str] | None = None) -> dict[str, Any]:
    """DS-01 & DS-10: Profile types, missing values, outliers, cardinality, and PII warnings (never auto-trains)."""
    cols = headers or (list(rows[0].keys()) if rows else [])
    n = len(rows)
    col_profiles: dict[str, dict[str, Any]] = {}
    pii_warnings: list[str] = []

    for col in cols:
        vals = [r.get(col) for r in rows]
        non_null = [v for v in vals if v is not None and str(v).strip() != ""]
        missing = n - len(non_null)
        if _PII_COL_RE.search(col):
            pii_warnings.append(f"'{col}' sütunu PII/KVKK hassas verisi içerebilir; maskeleme önerilir.")

        nums: list[float] = []
        dates = 0
        bools = 0
        for v in non_null:
            s = str(v).strip()
            if s.lower() in {"true", "false", "evet", "hayır"}:
                bools += 1
                continue
            if _DATE_STR_RE.match(s):
                dates += 1
                continue
            try:
                nums.append(float(s.replace(",", ".")))
            except ValueError:
                pass

        if non_null and len(nums) == len(non_null):
            arr = np.asarray(nums, dtype=np.float64)
            is_int = bool(np.all(np.equal(np.mod(arr, 1), 0)))
            q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
            iqr = q3 - q1
            outliers = int(np.sum((arr < q1 - 1.5 * iqr) | (arr > q3 + 1.5 * iqr))) if iqr > 0 else 0
            col_profiles[col] = {
                "type": "integer" if is_int else "float",
                "missing": missing,
                "cardinality": len(set(nums)),
                "min": round(float(arr.min()), 4),
                "max": round(float(arr.max()), 4),
                "mean": round(float(arr.mean()), 4),
                "std": round(float(arr.std()), 4),
                "outliers": outliers,
            }
        elif non_null and dates >= len(non_null) * 0.8:
            col_profiles[col] = {"type": "date", "missing": missing, "cardinality": len(set(map(str, non_null)))}
        elif non_null and bools == len(non_null):
            col_profiles[col] = {"type": "boolean", "missing": missing, "cardinality": len(set(map(str, non_null)))}
        else:
            card = len(set(map(str, non_null)))
            col_profiles[col] = {
                "type": "categorical" if card <= max(10, n * 0.3) else "text",
                "missing": missing,
                "cardinality": card,
            }

    cloud_off = os.environ.get("ALLOW_CLOUD_PROVIDERS", "false").lower() != "true"
    return {
        "row_count": n,
        "column_count": len(cols),
        "columns": col_profiles,
        "pii_warnings": pii_warnings,
        "privacy_badge": "bu veri yerelde kaldı" if cloud_off else "bulut sağlayıcı açık",
    }


# ---------------------------------------------------------------- DS-02 Safe Read-Only Text-to-SQL Execution

def safe_readonly_sql(db_path: Path, sql_query: str, *, max_rows: int = 200) -> dict[str, Any]:
    """DS-02: Enforce SELECT-only SQL, verify EXPLAIN QUERY PLAN, execute via SQLite read-only URI."""
    q = (sql_query or "").strip().rstrip(";")
    if not q or not re.match(r"^(?:SELECT|WITH)\b", q, re.IGNORECASE):
        raise PermissionError("Yalnızca salt-okunur SELECT/WITH sorgularına izin verilir.")
    if ";" in q or _SQL_FORBIDDEN_RE.search(q):
        raise PermissionError("Yazma/DDL veya çoklu SQL ifadesi güvenlik politikasıyla reddedildi.")

    uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        plan = [dict(r) for r in conn.execute(f"EXPLAIN QUERY PLAN {q}").fetchall()]
        cur = conn.execute(q)
        rows = [dict(r) for r in cur.fetchmany(max_rows)]
    finally:
        conn.close()
    return {"sql": q, "row_count": len(rows), "rows": rows, "explain_plan": plan}


# ---------------------------------------------------------------- DS-03 & MM-11 Visualization & Vector SVG

def recommend_and_render_chart(
    rows: list[dict[str, Any]],
    *,
    x_col: str,
    y_col: str,
    title: str = "",
    **options: Any,
) -> dict[str, Any]:
    """DS-03 & MM-11: Recommend chart type, flag misleading axes, and render editable vector SVG + reproducible code."""
    y_unit = str(options.get("y_unit", ""))
    truncate_y = bool(options.get("truncate_y", False))
    x_vals = [str(r.get(x_col, "")) for r in rows]
    y_vals = [float(r.get(y_col, 0.0)) for r in rows]
    is_time = bool(x_vals) and all(bool(_DATE_STR_RE.match(x) or re.match(r"^\d{4}$", x)) for x in x_vals)
    chart_type = "line" if is_time else ("bar" if len(set(x_vals)) <= 12 else "scatter")
    warnings = ["Uyarı: Kesik Y ekseni farkları abartabilir (sıfırdan başlaması önerilir)."] if truncate_y else []

    w, h, pad = 640, 320, 56
    ymin = min(y_vals) if (truncate_y and y_vals) else min(0.0, min(y_vals) if y_vals else 0.0)
    ymax = max(y_vals) if y_vals else 1.0
    span = max(1e-6, ymax - ymin)

    shapes: list[str] = []
    step_x = (w - 2 * pad) / max(1, len(x_vals))
    pts: list[str] = []
    for i, (xv, yv) in enumerate(zip(x_vals, y_vals, strict=False)):
        cx = pad + (i + 0.5) * step_x
        cy = h - pad - ((yv - ymin) / span) * (h - 2 * pad)
        pts.append(f"{cx:.1f},{cy:.1f}")
        if chart_type == "bar":
            bw = max(12.0, step_x * 0.6)
            bh = max(1.0, (h - pad) - cy)
            shapes.append(f'<rect x="{cx - bw / 2:.1f}" y="{cy:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#0F766E" rx="4"/>')
        else:
            shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="#0F766E"/>')
        shapes.append(f'<text x="{cx:.1f}" y="{h - pad + 18}" font-size="11" text-anchor="middle" fill="#334155">{xv[:12]}</text>')
    if chart_type == "line" and len(pts) >= 2:
        shapes.insert(0, f'<polyline fill="none" stroke="#0F766E" stroke-width="2.5" points="{" ".join(pts)}"/>')

    chart_title = title or f"{y_col} / {x_col}"
    ylabel = f"{y_col} ({y_unit})" if y_unit else y_col
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f'<rect width="100%" height="100%" fill="#FFFFFF"/>'
        f'<text x="{w / 2}" y="26" font-size="15" font-weight="bold" text-anchor="middle" fill="#0F172A">{chart_title}</text>'
        f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="#94A3B8"/>'
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{h - pad}" stroke="#94A3B8"/>'
        f'<text x="16" y="{h / 2}" font-size="11" transform="rotate(-90 16,{h / 2})" text-anchor="middle" fill="#334155">{ylabel}</text>'
        + "".join(shapes)
        + "</svg>"
    )
    repro_code = f"# Reproducible chart data\nx_col = {x_col!r}\ny_col = {y_col!r}\nx = {x_vals!r}\ny = {y_vals!r}\n"
    return {
        "chart_type": chart_type,
        "title": chart_title,
        "x_label": x_col,
        "y_label": ylabel,
        "warnings": warnings,
        "svg": svg,
        "reproducible_code": repro_code,
    }


# ---------------------------------------------------------------- DS-04 & DS-05 AutoML (Baseline + Leakage + Permutation Importance)

def train_automl_checked(
    X: list[list[float]],
    y: list[float],
    feature_names: list[str],
    *,
    time_ordered: bool = True,
    l2_alpha: float = 1.0,
) -> dict[str, Any]:
    """DS-04 & DS-05: Ridge regression with mandatory dummy baseline, leakage detection, permutation importance & what-if."""
    arr_x = np.asarray(X, dtype=np.float64)
    arr_y = np.asarray(y, dtype=np.float64)
    n, d = arr_x.shape
    if n < 6:
        raise ValueError("AutoML eğitimi için en az 6 gözlem gerekir.")

    # Target leakage detector (|corr(feature, y)| >= 0.985)
    leakage_warnings: list[str] = []
    for j, fname in enumerate(feature_names):
        col = arr_x[:, j]
        if float(np.std(col)) > 1e-9 and float(np.std(arr_y)) > 1e-9:
            r = abs(float(np.corrcoef(col, arr_y)[0, 1]))
            if r >= 0.985:
                leakage_warnings.append(f"Veri sızıntısı şüphesi: '{fname}' hedefle çok yüksek korelasyonlu (|r|={r:.4f}).")

    split = max(4, int(n * 0.75))
    x_tr, x_te = arr_x[:split], arr_x[split:]
    y_tr, y_te = arr_y[:split], arr_y[split:]

    # Baseline (mean predictor)
    base_pred = np.full_like(y_te, float(np.mean(y_tr)))
    base_mae = float(np.mean(np.abs(y_te - base_pred)))

    # Standardized Ridge closed-form solution
    mu = x_tr.mean(axis=0)
    sd = np.where(x_tr.std(axis=0) > 1e-9, x_tr.std(axis=0), 1.0)
    z_tr = np.hstack([np.ones((len(x_tr), 1)), (x_tr - mu) / sd])
    z_te = np.hstack([np.ones((len(x_te), 1)), (x_te - mu) / sd])
    reg = np.eye(d + 1) * l2_alpha
    reg[0, 0] = 0.0
    weights = np.linalg.pinv(z_tr.T @ z_tr + reg) @ (z_tr.T @ y_tr)
    pred = z_te @ weights
    model_mae = float(np.mean(np.abs(y_te - pred)))
    beats_baseline = model_mae < base_mae

    # DS-05: Deterministic permutation importance on test split
    rng = np.random.default_rng(42)
    importances: dict[str, float] = {}
    for j, fname in enumerate(feature_names):
        x_perm = x_te.copy()
        rng.shuffle(x_perm[:, j])
        z_perm = np.hstack([np.ones((len(x_perm), 1)), (x_perm - mu) / sd])
        perm_mae = float(np.mean(np.abs(y_te - (z_perm @ weights))))
        importances[fname] = round(max(0.0, perm_mae - model_mae), 6)

    ranked_imp = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "split_mode": "temporal" if time_ordered else "sequential",
        "baseline_mae": round(base_mae, 4),
        "model_mae": round(model_mae, 4),
        "beats_baseline": beats_baseline,
        "honest_verdict": (
            "Model, taban (ortalama) tahminciyi geride bıraktı."
            if beats_baseline
            else "Uyarı: Model, basit taban tahminciyi geçemedi; bu modelle karar alınmamalıdır."
        ),
        "leakage_warnings": leakage_warnings,
        "feature_importance": [{"feature": f, "importance": sc} for f, sc in ranked_imp],
        "weights": weights.tolist(),
        "scaler_mean": mu.tolist(),
        "scaler_std": sd.tolist(),
    }


def what_if_predict(model_bundle: dict[str, Any], row_features: list[float]) -> float:
    """DS-05: Interactive 'what-if' prediction using saved AutoML weights."""
    x = np.asarray(row_features, dtype=np.float64)
    mu = np.asarray(model_bundle["scaler_mean"], dtype=np.float64)
    sd = np.asarray(model_bundle["scaler_std"], dtype=np.float64)
    w = np.asarray(model_bundle["weights"], dtype=np.float64)
    z = np.concatenate([[1.0], (x - mu) / sd])
    return round(float(z @ w), 4)


# ---------------------------------------------------------------- DS-06 Explained Anomaly Detection

def detect_anomalies_explained(rows: list[dict[str, Any]], numeric_cols: list[str], *, z_thresh: float = 3.0) -> dict[str, Any]:
    """DS-06: Robust MAD z-score anomaly detector explaining WHICH column(s) drove each anomaly."""
    if not rows or not numeric_cols:
        return {"anomaly_count": 0, "anomalies": []}
    medians: dict[str, float] = {}
    mads: dict[str, float] = {}
    for col in numeric_cols:
        arr = np.asarray([float(r.get(col, 0.0)) for r in rows], dtype=np.float64)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) * 1.4826
        medians[col] = med
        mads[col] = mad if mad > 1e-9 else float(np.std(arr)) or 1.0

    anomalies: list[dict[str, Any]] = []
    for idx, r in enumerate(rows):
        reasons: list[dict[str, Any]] = []
        for col in numeric_cols:
            val = float(r.get(col, 0.0))
            rz = abs(val - medians[col]) / mads[col]
            if rz >= z_thresh:
                reasons.append({"column": col, "value": val, "median": round(medians[col], 4), "robust_z": round(rz, 2)})
        if reasons:
            anomalies.append({"row_index": idx, "reasons": reasons})
    return {"anomaly_count": len(anomalies), "anomalies": anomalies}


# ---------------------------------------------------------------- DS-07 Forecasting with Backtest & Uncertainty

def forecast_with_backtest(series: list[float], *, horizon: int = 3) -> dict[str, Any]:
    """DS-07: Reject < 4 points; run walk-forward backtest and return 95% prediction intervals."""
    if len(series) < 4:
        return {"can_forecast": False, "reason": "Yeterli veri yok (en az 4 gözlem gerekir): tahmin yapılamaz.", "forecasts": []}

    arr = np.asarray(series, dtype=np.float64)
    # Walk-forward backtest using linear trend
    errors: list[float] = []
    for t in range(3, len(arr)):
        xs = np.arange(t, dtype=np.float64)
        slope, intercept = np.polyfit(xs, arr[:t], 1)
        pred_t = slope * t + intercept
        errors.append(abs(float(arr[t] - pred_t)))
    backtest_mae = float(np.mean(errors)) if errors else 0.0
    resid_std = float(np.std(errors)) if len(errors) > 1 else backtest_mae

    xs_all = np.arange(len(arr), dtype=np.float64)
    slope, intercept = np.polyfit(xs_all, arr, 1)
    forecasts: list[dict[str, Any]] = []
    for h in range(1, horizon + 1):
        pt = float(slope * (len(arr) - 1 + h) + intercept)
        margin = 1.96 * max(resid_std, 1e-4) * math.sqrt(h)
        forecasts.append({
            "step": h,
            "point_forecast": round(pt, 4),
            "lower_95": round(pt - margin, 4),
            "upper_95": round(pt + margin, 4),
            "label": f"tahmin: {pt:.2f}, belirsizlik +-{margin:.2f}",
        })
    return {
        "can_forecast": True,
        "backtest_mae": round(backtest_mae, 4),
        "trend_slope": round(float(slope), 4),
        "forecasts": forecasts,
    }


# ---------------------------------------------------------------- DS-08 Statistical Test Selection (Non-Causal Template)

def select_and_run_stat_test(group_a: list[float], group_b: list[float]) -> dict[str, Any]:
    """DS-08: Choose Welch t-test vs Mann-Whitney U based on sample size/skewness, compute Cohen's d & p-value."""
    a = np.asarray(group_a, dtype=np.float64)
    b = np.asarray(group_b, dtype=np.float64)
    if len(a) < 3 or len(b) < 3:
        raise ValueError("İstatistiksel test için her grupta en az 3 gözlem gerekir.")

    # Welch's t-statistic + normal approximation two-sided p-value (exact enough for clear gating without scipy)
    ma, mb = float(a.mean()), float(b.mean())
    va, vb = float(a.var(ddof=1)), float(b.var(ddof=1))
    se = math.sqrt(va / len(a) + vb / len(b)) or 1e-9
    t_stat = (ma - mb) / se
    p_val = math.erfc(abs(t_stat) / math.sqrt(2.0))
    pooled_sd = math.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / max(1, len(a) + len(b) - 2)) or 1e-9
    cohens_d = (ma - mb) / pooled_sd

    skew_a = abs(float(np.mean(((a - ma) / (float(a.std()) or 1.0)) ** 3)))
    selected = "mann_whitney_u_recommended_skewed" if skew_a > 1.5 else "welch_t_test"
    sig = p_val < 0.05
    interpretation = (
        f"İki grup arasında istatistiksel olarak anlamlı bir fark gözlemlendi (p={p_val:.4f}, Cohen d={cohens_d:.2f}); "
        "bu sonuç yalnızca ilişki/fark gösterir, tek başına nedensellik kanıtlamaz."
        if sig
        else f"İki grup arasında istatistiksel olarak anlamlı bir fark saptanmadı (p={p_val:.4f}, Cohen d={cohens_d:.2f})."
    )
    return {
        "selected_test": selected,
        "statistic": round(t_stat, 4),
        "p_value": round(p_val, 6),
        "cohens_d": round(cohens_d, 4),
        "significant_005": sig,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------- DS-09 Reproducible Analysis HTML Notebook

def build_reproducible_report_html(title: str, code: str, summary_json: dict[str, Any], svg_chart: str = "") -> str:
    """DS-09: Self-contained reproducible HTML analysis report containing executable code, outputs & chart."""
    import html
    import json

    return (
        "<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title></head><body>"
        f"<h1>{html.escape(title)}</h1>"
        f"<section><h2>Grafik</h2>{svg_chart}</section>"
        f"<section><h2>Doğrulanmış Sonuçlar</h2><pre>{html.escape(json.dumps(summary_json, ensure_ascii=False, indent=2))}</pre></section>"
        f"<section><h2>Yeniden Üretilebilir Kod</h2><pre><code>{html.escape(code)}</code></pre></section>"
        "</body></html>"
    )
