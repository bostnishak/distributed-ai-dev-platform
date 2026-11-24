"""Domain Experts Engine [M57]: Legal Contract Risk & Clause Analyzer, Corporate Finance CFO Valuation & Monte Carlo, Academic Research & Taguchi Design of Experiments (DoE), and Natural-Language Text-to-SQL & Schema ERD Introspector.

100% local, deterministic, zero-emoji, production-grade implementation.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from domain_experts_helpers import (
    _CLAUSE_CATALOG,
    _TAGUCHI_L4,
    _TAGUCHI_L8,
    _TAGUCHI_L9,
    analyze_legal_contract,
    compute_taguchi_sn_ratio,
    format_academic_citation,
    generate_taguchi_doe,
)

# ============================================================================
# 2. CORPORATE FINANCE, CFO RATIO, 5-YEAR DCF VALUATION & MONTE CARLO ENGINE
# ============================================================================

_CFO_DEFAULTS: tuple[tuple[str, Any], ...] = (
    ("revenue", 10_000_000.0),
    ("cogs", 6_000_000.0),
    ("ebitda", 2_500_000.0),
    ("net_income", 1_400_000.0),
    ("current_assets", 4_000_000.0),
    ("inventory", 1_200_000.0),
    ("current_liabilities", 2_000_000.0),
    ("total_assets", 12_000_000.0),
    ("total_debt", 3_500_000.0),
    ("total_equity", 6_500_000.0),
    ("initial_fcf", None),
    ("growth_rate", 0.12),
    ("wacc", 0.10),
    ("terminal_growth_rate", 0.03),
    ("initial_investment", 5_000_000.0),
    ("growth_volatility", 0.04),
    ("wacc_volatility", 0.015),
    ("monte_carlo_runs", 500),
    ("random_seed", 42),
)


def _merge_cfo_params(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    params = dict(_CFO_DEFAULTS)
    for (name, _), val in zip(_CFO_DEFAULTS, args, strict=False):
        params[name] = val
    params.update(kwargs)
    return params


def _compute_cfo_ratios(p: dict[str, Any]) -> dict[str, float]:
    safe_rev = max(1e-9, float(p["revenue"]))
    safe_cl = max(1e-9, float(p["current_liabilities"]))
    safe_eq = max(1e-9, float(p["total_equity"]))
    safe_ta = max(1e-9, float(p["total_assets"]))
    return {
        "current_ratio": round(float(p["current_assets"]) / safe_cl, 4),
        "quick_ratio": round((float(p["current_assets"]) - float(p["inventory"])) / safe_cl, 4),
        "gross_margin": round((float(p["revenue"]) - float(p["cogs"])) / safe_rev, 4),
        "ebitda_margin": round(float(p["ebitda"]) / safe_rev, 4),
        "roe": round(float(p["net_income"]) / safe_eq, 4),
        "roa": round(float(p["net_income"]) / safe_ta, 4),
        "debt_to_equity": round(float(p["total_debt"]) / safe_eq, 4),
    }


def _run_cfo_monte_carlo(p: dict[str, Any], base_fcf: float, effective_wacc: float) -> dict[str, Any]:
    runs = max(100, int(p["monte_carlo_runs"]))
    rng = np.random.default_rng(int(p["random_seed"]))
    term_g = float(p["terminal_growth_rate"])
    sim_growth = rng.normal(loc=float(p["growth_rate"]), scale=max(1e-6, float(p["growth_volatility"])), size=(runs, 5))
    sim_wacc = np.clip(
        rng.normal(loc=effective_wacc, scale=max(1e-6, float(p["wacc_volatility"])), size=runs),
        term_g + 0.008,
        0.50,
    )
    sim_fcfs = base_fcf * np.cumprod(1.0 + sim_growth, axis=1)
    years_arr = np.arange(1, 6, dtype=np.float64)
    pv_fcfs_sim = np.sum(sim_fcfs / ((1.0 + sim_wacc[:, None]) ** years_arr[None, :]), axis=1)
    pv_term_sim = (sim_fcfs[:, -1] * (1.0 + term_g) / (sim_wacc - term_g)) / ((1.0 + sim_wacc) ** 5)
    npv_sim = pv_fcfs_sim + pv_term_sim - float(p["initial_investment"])
    p10, p50, p90 = np.percentile(npv_sim, [10, 50, 90])
    return {
        "runs": runs,
        "p10_npv": round(float(p10), 2),
        "p50_npv": round(float(p50), 2),
        "p90_npv": round(float(p90), 2),
        "mean_npv": round(float(np.mean(npv_sim)), 2),
        "std_npv": round(float(np.std(npv_sim)), 2),
        "prob_positive_npv": round(float(np.mean(npv_sim > 0.0)), 4),
    }


def run_cfo_financial_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compute CFO liquidity/profitability/leverage ratios, 5-Year DCF enterprise valuation, and a 500-run NumPy Monte Carlo NPV simulation."""
    p = _merge_cfo_params(args, kwargs)
    ratios = _compute_cfo_ratios(p)

    base_fcf = float(p["initial_fcf"]) if p["initial_fcf"] is not None else float(p["ebitda"]) * 0.65
    term_g = float(p["terminal_growth_rate"])
    growth = float(p["growth_rate"])
    effective_wacc = max(float(p["wacc"]), term_g + 0.01)

    projected_fcfs = [round(base_fcf * ((1.0 + growth) ** yr), 2) for yr in range(1, 6)]
    discounted_fcfs = [round(fcf / ((1.0 + effective_wacc) ** yr), 2) for yr, fcf in enumerate(projected_fcfs, start=1)]
    pv_of_fcfs = float(sum(discounted_fcfs))
    terminal_value = (projected_fcfs[-1] * (1.0 + term_g)) / (effective_wacc - term_g)
    pv_terminal_value = terminal_value / ((1.0 + effective_wacc) ** 5)
    enterprise_value = pv_of_fcfs + pv_terminal_value
    base_npv = enterprise_value - float(p["initial_investment"])

    return {
        "ratios": ratios,
        "dcf": {
            "base_fcf": round(base_fcf, 2),
            "wacc": round(effective_wacc, 4),
            "terminal_growth_rate": round(term_g, 4),
            "projected_fcfs": projected_fcfs,
            "discounted_fcfs": discounted_fcfs,
            "pv_of_fcfs": round(pv_of_fcfs, 2),
            "terminal_value": round(terminal_value, 2),
            "pv_terminal_value": round(pv_terminal_value, 2),
            "enterprise_value": round(enterprise_value, 2),
            "base_npv": round(base_npv, 2),
        },
        "monte_carlo": _run_cfo_monte_carlo(p, base_fcf, effective_wacc),
    }


# ============================================================================
# 4. NATURAL-LANGUAGE TEXT-TO-SQL & SCHEMA ERD INTROSPECTOR
# ============================================================================

_FORBIDDEN_SQL_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)


def _validate_readonly_select(sql: str) -> str:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("SQL query cannot be empty")
    if ";" in cleaned:
        raise ValueError("Multiple SQL statements are prohibited in read-only mode")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, flags=re.IGNORECASE):
        raise ValueError("Only read-only SELECT queries are permitted")
    if _FORBIDDEN_SQL_RE.search(cleaned):
        raise ValueError("Mutating or administrative SQL keywords are prohibited in read-only mode")
    return cleaned


def _pick_target_table(tables: list[dict[str, Any]], q_lower: str) -> dict[str, Any]:
    for tbl in tables:
        tname = tbl["name"].lower()
        tname_singular = tname.rstrip("s")
        if tname in q_lower or (len(tname_singular) >= 3 and tname_singular in q_lower):
            return tbl
    return tables[0]


def _pick_mentioned_column(candidates: list[str], q_lower: str, default_col: str) -> str:
    for col in candidates:
        if col.lower() in q_lower:
            return col
    return default_col


def _translate_natural_query_to_sql(natural_query: str, schema: dict[str, Any]) -> str:
    """Deterministically translate a Turkish/English natural language query into a safe SELECT query."""
    tables: list[dict[str, Any]] = schema.get("tables", [])
    if not tables:
        raise ValueError("Database contains no user tables to query")

    import sql_safe

    q_lower = (natural_query or "").lower()
    target_table = _pick_target_table(tables, q_lower)
    t_name = target_table["name"]
    col_names = [c["name"] for c in target_table["columns"]]
    numeric_cols = [
        c["name"]
        for c in target_table["columns"]
        if any(k in (c["type"] or "").upper() for k in ("INT", "REAL", "NUM", "DEC", "FLOAT", "DOUBLE"))
        and not c["pk"]
    ]

    if any(k in q_lower for k in ("kaç", "kac", "sayısı", "sayisi", "count", "how many", "toplam kayıt")):
        return sql_safe.build_select(t_name, "COUNT(*) AS total_count")

    if numeric_cols and any(k in q_lower for k in ("toplam", "sum", "total")):
        target_col = _pick_mentioned_column(numeric_cols, q_lower, numeric_cols[0])
        return sql_safe.build_select(t_name, f"SUM({sql_safe.safe_ident(target_col)}) AS total_{target_col}, COUNT(*) AS row_count")

    if numeric_cols and any(k in q_lower for k in ("ortalama", "average", "avg", "mean")):
        target_col = _pick_mentioned_column(numeric_cols, q_lower, numeric_cols[0])
        return sql_safe.build_select(t_name, f"AVG({sql_safe.safe_ident(target_col)}) AS avg_{target_col}, COUNT(*) AS row_count")

    order_clause = ""
    if any(k in q_lower for k in ("en yüksek", "en buyuk", "en büyük", "top", "highest", "most", "descending")):
        default_sort = numeric_cols[0] if numeric_cols else col_names[0]
        sort_col = _pick_mentioned_column(col_names, q_lower, default_sort)
        order_clause = f"{sql_safe.safe_ident(sort_col)} DESC"

    m_lim = re.search(r"\b(?:ilk|top|limit)\s+(\d{1,4})\b", q_lower)
    limit_val = min(500, max(1, int(m_lim.group(1)))) if m_lim else 50
    return sql_safe.build_select(t_name, "*", order_by=order_clause, limit=limit_val)


def introspect_sqlite_and_query(
    db_path: Path | str,
    natural_query: str,
    sql_override: str | None = None,
) -> dict[str, Any]:
    """Introspect tables, columns, primary/foreign keys of a SQLite DB, generate a Mermaid erDiagram, safely execute a read-only SELECT query, and return structured rows + summary."""
    resolved_path = Path(db_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {resolved_path}")

    uri = f"file:{resolved_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        table_names = [row["name"] for row in cur.fetchall()]

        tables_meta: list[dict[str, Any]] = []
        relationships: list[dict[str, str]] = []
        mermaid_lines: list[str] = ["erDiagram"]

        for tname in table_names:
            cur.execute(f"PRAGMA table_info('{tname}')")
            cols_raw = cur.fetchall()
            cols_list: list[dict[str, Any]] = []
            mermaid_lines.append(f"    {tname} {{")
            for c in cols_raw:
                col_type = (c["type"] or "TEXT").split("(")[0].strip().upper() or "TEXT"
                is_pk = bool(c["pk"])
                cols_list.append(
                    {
                        "name": c["name"],
                        "type": c["type"] or "TEXT",
                        "notnull": bool(c["notnull"]),
                        "pk": is_pk,
                    }
                )
                pk_tag = " PK" if is_pk else ""
                mermaid_lines.append(f"        {col_type} {c['name']}{pk_tag}")
            mermaid_lines.append("    }")

            cur.execute(f"PRAGMA foreign_key_list('{tname}')")
            fks_raw = cur.fetchall()
            fks_list: list[dict[str, str]] = []
            for fk in fks_raw:
                rel = {
                    "from_table": tname,
                    "from_column": fk["from"],
                    "to_table": fk["table"],
                    "to_column": fk["to"],
                }
                fks_list.append(rel)
                relationships.append(rel)
                mermaid_lines.append(f'    {fk["table"]} ||--o{{ {tname} : "{fk["from"]}"')

            tables_meta.append({"name": tname, "columns": cols_list, "foreign_keys": fks_list})

        schema_info = {"tables": tables_meta, "relationships": relationships}
        raw_sql = sql_override if sql_override is not None else _translate_natural_query_to_sql(natural_query, schema_info)
        safe_sql = _validate_readonly_select(raw_sql)

        cur.execute(safe_sql)
        rows = [dict(r) for r in cur.fetchall()]
        columns = list(rows[0].keys()) if rows else [d[0] for d in (cur.description or [])]

        summary = (
            f"Executed read-only query on {len(tables_meta)} table(s); "
            f"returned {len(rows)} row(s) across {len(columns)} column(s)."
        )

        return {
            "db_path": str(resolved_path),
            "schema": schema_info,
            "er_diagram": "\n".join(mermaid_lines),
            "executed_sql": safe_sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "summary": summary,
        }
    finally:
        conn.close()


__all__ = [
    "_CLAUSE_CATALOG",
    "_TAGUCHI_L4",
    "_TAGUCHI_L8",
    "_TAGUCHI_L9",
    "analyze_legal_contract",
    "compute_taguchi_sn_ratio",
    "format_academic_citation",
    "generate_taguchi_doe",
    "introspect_sqlite_and_query",
    "run_cfo_financial_analysis",
]
