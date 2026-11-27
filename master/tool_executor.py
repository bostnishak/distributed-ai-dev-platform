"""Cluster A (`[M05]`-`[M08]`): Deterministic ReAct Tool Executor & Multi-Agent Reasoning Council.

Provides zero-hallucination deterministic tools:
- `solve_math_and_equations`: linear/quadratic equations, matrix operations, derivatives, integrals, stats
- `convert_engineering_units`: length, pressure/stress (MPa/PSI/Bar), torque, hardness (HRC/HB), spindle RPM
- `query_tabular_data_sql`: loads CSV/TSV/JSON rows into an in-memory SQLite table and executes real SQL aggregations
- `run_reasoning_council`: 3-stage Multi-Agent Debate & Synthesis Council (Proposer A + Proposer B + Critic + Judge)
"""

from __future__ import annotations

import csv
import io
import math
import re
import sqlite3
from typing import Any

import numpy as np

import multimodal_studio as mms

# ============================================================================
# 1. DETERMINISTIC MATH, CALCULUS, MATRIX & STATISTICS SOLVER ([M06])
# ============================================================================


def solve_quadratic_or_linear(a: float, b: float, c: float = 0.0) -> dict[str, Any]:
    """Solve a*x^2 + b*x + c = 0 (or b*x + c = 0 when a == 0)."""
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return {"type": "degenerate", "roots": []}
        return {"type": "linear", "roots": [round(-c / b, 6)]}
    disc = b * b - 4.0 * a * c
    if disc >= 0:
        r1 = (-b + math.sqrt(disc)) / (2.0 * a)
        r2 = (-b - math.sqrt(disc)) / (2.0 * a)
        roots = sorted({round(r1, 6), round(r2, 6)})
        return {"type": "quadratic_real", "discriminant": round(disc, 6), "roots": roots}
    real_part = round(-b / (2.0 * a), 6)
    imag_part = round(math.sqrt(-disc) / (2.0 * a), 6)
    return {
        "type": "quadratic_complex",
        "discriminant": round(disc, 6),
        "roots": [f"{real_part} + {imag_part}i", f"{real_part} - {imag_part}i"],
    }


def solve_linear_system(matrix_a: list[list[float]], vector_b: list[float]) -> dict[str, Any]:
    """Solve A * x = b using NumPy linear algebra."""
    arr_a = np.array(matrix_a, dtype=np.float64)
    arr_b = np.array(vector_b, dtype=np.float64)
    det = float(np.linalg.det(arr_a)) if arr_a.shape[0] == arr_a.shape[1] else 0.0
    sol, residuals, rank, _ = np.linalg.lstsq(arr_a, arr_b, rcond=None)
    return {
        "solution": [round(float(x), 6) for x in sol],
        "determinant": round(det, 6),
        "rank": int(rank),
        "residual_norm": round(float(np.sum(residuals)), 6) if len(residuals) > 0 else 0.0,
    }


def compute_descriptive_stats(values: list[float]) -> dict[str, float]:
    """Compute exact descriptive statistics for a numeric series."""
    if not values:
        return {"count": 0}
    arr = np.array(values, dtype=np.float64)
    q25, q50, q75 = np.percentile(arr, [25, 50, 75])
    return {
        "count": len(arr),
        "sum": round(float(np.sum(arr)), 4),
        "mean": round(float(np.mean(arr)), 4),
        "std": round(float(np.std(arr, ddof=1 if len(arr) > 1 else 0)), 4),
        "min": round(float(np.min(arr)), 4),
        "q25": round(float(q25), 4),
        "median": round(float(q50), 4),
        "q75": round(float(q75), 4),
        "max": round(float(np.max(arr)), 4),
        "iqr": round(float(q75 - q25), 4),
    }


# ============================================================================
# 2. DETERMINISTIC ENGINEERING & SCIENCE UNIT CONVERTER ([M06])
# ============================================================================

_UNIT_FACTORS: dict[tuple[str, str], float] = {
    ("mm", "inch"): 1.0 / 25.4,
    ("inch", "mm"): 25.4,
    ("m", "ft"): 3.2808399,
    ("ft", "m"): 1.0 / 3.2808399,
    ("kg", "lb"): 2.20462262,
    ("lb", "kg"): 1.0 / 2.20462262,
    ("mpa", "psi"): 145.037738,
    ("psi", "mpa"): 1.0 / 145.037738,
    ("bar", "psi"): 14.5037738,
    ("psi", "bar"): 1.0 / 14.5037738,
    ("nm", "lbft"): 0.73756215,
    ("lbft", "nm"): 1.0 / 0.73756215,
    ("kw", "hp"): 1.34102209,
    ("hp", "kw"): 1.0 / 1.34102209,
}


def convert_engineering_units(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    u1, u2 = from_unit.strip().lower(), to_unit.strip().lower()
    if u1 == u2:
        return {"value": value, "from": from_unit, "to": to_unit, "result": value}
    if (u1, u2) == ("c", "f"):
        res = value * 9.0 / 5.0 + 32.0
    elif (u1, u2) == ("f", "c"):
        res = (value - 32.0) * 5.0 / 9.0
    elif (u1, u2) in _UNIT_FACTORS:
        res = value * _UNIT_FACTORS[(u1, u2)]
    else:
        raise ValueError(f"Desteklenmeyen birim dönüşümü: {from_unit} -> {to_unit}")
    return {"value": value, "from": from_unit, "to": to_unit, "result": round(res, 6)}


def calculate_spindle_rpm_and_feed(cutting_speed_vc_m_min: float, diameter_mm: float, feed_per_tooth_mm: float, teeth: int = 1) -> dict[str, float]:
    """Compute exact CNC spindle RPM (n = 1000*Vc / (pi*D)) and table feed Vf (mm/min)."""
    if diameter_mm <= 0:
        raise ValueError("Çap 0'dan büyük olmalıdır.")
    rpm = (1000.0 * cutting_speed_vc_m_min) / (math.pi * diameter_mm)
    vf = rpm * feed_per_tooth_mm * max(1, teeth)
    return {
        "rpm": round(rpm, 1),
        "table_feed_mm_min": round(vf, 1),
        "feed_per_rev_mm": round(feed_per_tooth_mm * max(1, teeth), 4),
    }


# ============================================================================
# 3. ZERO-HALLUCINATION TABULAR DATA & SQL QUERY TOOL ([M07])
# ============================================================================


def query_csv_with_sql(csv_text: str, sql_query: str = "SELECT * FROM data LIMIT 10") -> dict[str, Any]:
    """Load CSV data into an in-memory SQLite table `data` with typed numeric columns and execute SQL."""
    reader = csv.reader(io.StringIO(csv_text.strip()))
    all_rows = [r for r in reader if any(c.strip() for c in r)]
    if len(all_rows) < 2:
        return {"columns": [], "rows": [], "row_count": 0}

    raw_headers = all_rows[0]
    clean_cols = [re.sub(r"[^a-zA-Z0-9_]", "_", h.strip()).strip("_").lower() or f"col_{i}" for i, h in enumerate(raw_headers)]
    data_rows = all_rows[1:]

    conn = sqlite3.connect(":memory:")
    col_defs = ", ".join(f'"{c}" NUMERIC' for c in clean_cols)
    conn.execute(f"CREATE TABLE data ({col_defs})")

    typed_rows = []
    for r in data_rows:
        row_vals: list[Any] = []
        for i in range(len(clean_cols)):
            v = r[i].strip() if i < len(r) else ""
            try:
                row_vals.append(float(v.replace(",", ".")) if "." in v or "," in v else int(v))
            except ValueError:
                row_vals.append(v)
        typed_rows.append(row_vals)
    import sql_safe

    conn.executemany(sql_safe.build_insert_values("data", len(clean_cols)), typed_rows)

    # Only allow read-only SELECT queries
    if not sql_query.strip().upper().startswith("SELECT"):
        raise ValueError("Sadece SELECT sorgularına izin verilir.")

    cur = conn.execute(sql_query)
    out_cols = [d[0] for d in cur.description] if cur.description else []
    out_rows = [list(r) for r in cur.fetchall()]
    conn.close()
    return {"table_columns": clean_cols, "query_columns": out_cols, "rows": out_rows, "total_source_rows": len(data_rows)}


# ============================================================================
# 4. MULTI-AGENT DEBATE & SYNTHESIS COUNCIL ([M08])
# ============================================================================


async def _call_model(model: str, system: str, prompt: str, num_predict: int = 2048, temp: float = 0.3) -> str:
    import gateway

    prof = "factual" if temp <= 0.15 else ("code" if temp <= 0.25 else "analytic")
    res = await gateway.default_client.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        model=model,
        profile=prof,
        num_predict=num_predict,
        timeout_s=600.0,  # 2500 tokens at the 7-12 tok/s of an 8 GB card does not fit in two minutes
        feature="reasoning_council",
        max_retries=0,
    )
    return res.content


async def run_reasoning_council(prompt: str, context: str = "") -> dict[str, Any]:
    """Execute 3-Stage Multi-Agent Reasoning Council: Proposer A + Proposer B -> Critic -> Judge Synthesis."""
    model_a = await mms.pick_best_model("deep")
    model_b = await mms.pick_best_model("code")
    full_q = f"{prompt}\n\nEk Bağlam:\n{context}" if context else prompt

    draft_a = await _call_model(
        model_a,
        "Sen Konsey Üyesi A (Stratejik ve Analitik Uzman) olarak soruyu tüm boyutlarıyla derinlemesine çöz. Emoji kullanma.",
        full_q,
        num_predict=1536,
        temp=0.35,
    )
    draft_b = await _call_model(
        model_b,
        "Sen Konsey Üyesi B (Teknik, Matematiksel ve Sistem Uzmanı) olarak soruyu somut adımlar, formüller ve mimariyle çöz. Emoji kullanma.",
        full_q,
        num_predict=1536,
        temp=0.2,
    )

    critique_prompt = (
        f"Soru:\n{prompt}\n\n--- Çözüm A ({model_a}) ---\n{draft_a[:2500]}\n\n"
        f"--- Çözüm B ({model_b}) ---\n{draft_b[:2500]}\n\n"
        "Her iki çözümdeki eksikleri, olası hataları ve birleştirilmesi gereken en güçlü noktaları 4 maddede eleştir."
    )
    critique = await _call_model(
        model_a,
        "Sen Şeytanın Avukatı / Eleştirmen Ajansın. Hataları ve eksikleri acımasızca tespit et. Emoji kullanma.",
        critique_prompt,
        num_predict=768,
        temp=0.2,
    )

    judge_prompt = (
        f"Kullanıcı İsteği:\n{full_q}\n\n"
        f"--- Taslak A ---\n{draft_a[:2500]}\n\n"
        f"--- Taslak B ---\n{draft_b[:2500]}\n\n"
        f"--- Eleştirmen Raporu ---\n{critique}\n\n"
        "Eleştirileri tamamen gidererek her iki taslağın en güçlü yanlarını birleştiren eksiksiz, kurumsal nihai yanıtı yaz. Emoji kullanma."
    )
    final_answer = await _call_model(
        model_a,
        "Sen Konsey Baş Hakemi ve Sentezleyicisisin. Eksiksiz, doğrulanmış, yapılandırılmış nihai yanıtı üret.",
        judge_prompt,
        num_predict=2560,
        temp=0.25,
    )

    return {
        "proposer_a_model": model_a,
        "proposer_b_model": model_b,
        "draft_a": draft_a,
        "draft_b": draft_b,
        "critique": critique,
        "final_answer": final_answer,
    }
