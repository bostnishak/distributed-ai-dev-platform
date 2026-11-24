"""Domain Experts Engine [M57]: Legal Contract Risk & Clause Analyzer, Corporate Finance CFO Valuation & Monte Carlo, Academic Research & Taguchi Design of Experiments (DoE), and Natural-Language Text-to-SQL & Schema ERD Introspector.

100% local, deterministic, zero-emoji, production-grade implementation.
"""

from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

# ============================================================================
# 1. LEGAL CONTRACT RISK & CLAUSE ANALYZER
# ============================================================================

_CLAUSE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "termination",
        "title": "Termination / Fesih",
        "detect_patterns": [
            r"\b(fesih|feshed\w*|sona\s+er\w*|termination|terminate\w*)\b",
        ],
        "high_risk_patterns": [
            r"(tek\s+tarafl[ıi]\w*\s+.*fes\w*|bildirimsiz\s+fes\w*|derhal\s+fes\w*|unilateral\w*\s+terminat\w*|terminate\s+at\s+any\s+time\s+without\s+notice|without\s+cause\s+immediately)",
        ],
        "medium_risk_patterns": [
            r"(hakl[ıi]\s+neden\s+olmaks[ıi]z[ıi]n|kolayl[ıi]kla\s+fes\w*|for\s+convenience|7\s+g[üu]n\s+[öo]nceden)",
        ],
        "essential": True,
        "redline_recommendation": (
            "Taraflardan herhangi biri, diğer tarafın sözleşmeyi esaslı şekilde ihlal etmesi ve "
            "yazılı ihtara rağmen 30 (otuz) gün içinde ihlali gidermemesi halinde sözleşmeyi feshedebilir. "
            "Tek taraflı derhal ve bildirimsiz fesih yetkisi karşılıklı yazılı mutabakata bağlanmıştır."
        ),
    },
    {
        "id": "unlimited_liability",
        "title": "Unlimited Liability / Tazminat",
        "detect_patterns": [
            r"\b(tazminat|sorumluluk|zarar\w*|liability|indemnif\w*|damages)\b",
        ],
        "high_risk_patterns": [
            r"(s[ıi]n[ıi]rs[ıi]z\s+sorumluluk|s[ıi]n[ıi]rs[ıi]z\s+tazminat|dolayl[ıi]\s+zarar\w*\s+dahil|k[âa]r\s+kayb[ıi]\s+dahil|her\s+t[üu]rl[üu]\s+zarardan\s+s[ıi]n[ıi]rs[ıi]z|unlimited\s+liability|all\s+indirect\s+and\s+consequential\s+damages|without\s+limit\w*\s+liab\w*)",
        ],
        "medium_risk_patterns": [
            r"(kusursuz\s+sorumluluk|strict\s+liability|s[öo]zle[şs]me\s+bedelinin\s+[3-9]\s+kat[ıi])",
        ],
        "essential": True,
        "redline_recommendation": (
            "Tarafların işbu sözleşme kapsamındaki toplam mali sorumluluğu, doğrudan zararlarla sınırlı "
            "olmak üzere son 12 ayda ödenen toplam sözleşme bedelini aşamaz. Kâr kaybı, itibar kaybı ve "
            "dolaylı zararlardan taraflar sorumlu tutulamaz."
        ),
    },
    {
        "id": "penalty",
        "title": "Penalty / Cezai Sart",
        "detect_patterns": [
            r"\b(cezai\s+[şs]art|ceza\s+bedeli|gecikme\s+cezas[ıi]|penalty|liquidated\s+damages)\b",
        ],
        "high_risk_patterns": [
            r"(tenkis\s+edilemez|indirim\s+talep\s+edemez|s[öo]zle[şs]me\s+bedelinin\s+%\s*(?:[3-9]\d|100)|g[üu]nl[üu]k\s+%\s*[2-9]|non-reducible\s+penalty|waives\s+any\s+right\s+to\s+reduction)",
        ],
        "medium_risk_patterns": [
            r"(cezai\s+[şs]art|liquidated\s+damages|gecikme\s+cezas[ıi])",
        ],
        "essential": False,
        "redline_recommendation": (
            "Cezai şart yalnızca kusurlu gecikme halinde, günlük %0.1 oranında ve toplamda ilgili iş "
            "kalemi bedelinin %10'unu aşmamak kaydıyla uygulanır; mücbir sebep halleri hariçtir."
        ),
    },
    {
        "id": "jurisdiction",
        "title": "Jurisdiction / Yetkili Mahkeme",
        "detect_patterns": [
            r"\b(yetkili\s+mahkeme|tahkim|uygulanacak\s+hukuk|icra\s+daire\w*|jurisdiction|governing\s+law|arbitration|courts)\b",
        ],
        "high_risk_patterns": [
            r"(yabanc[ıi]\s+mahkeme\w*\s+m[üu]nhas[ıi]ran|exclusive\s+jurisdiction\s+of\s+foreign|cayman|delaware\s+exclusively)",
        ],
        "medium_risk_patterns": [
            r"(tek\s+tarafl[ıi]\s+yetki|sole\s+discretion\s+forum)",
        ],
        "essential": True,
        "redline_recommendation": (
            "İşbu sözleşmeden doğacak uyuşmazlıklarda Türkiye Cumhuriyeti hukuku uygulanacak olup, "
            "İstanbul Merkez (Çağlayan) Mahkemeleri ve İcra Daireleri yetkilidir."
        ),
    },
    {
        "id": "confidentiality",
        "title": "Confidentiality / Gizlilik",
        "detect_patterns": [
            r"\b(gizlilik|gizli\s+bilgi\w*|s[ıi]r\s+saklama|confidential\w*|non-disclosure|nda)\b",
        ],
        "high_risk_patterns": [
            r"(s[üu]resiz\s+ve\s+tek\s+tarafl[ıi]\s+gizlilik|perpetual\s+unilateral\s+confidentiality)",
        ],
        "medium_risk_patterns": [
            r"(kamuya\s+a[çc][ıi]k\s+bilgiler\s+dahil|including\s+publicly\s+known)",
        ],
        "essential": True,
        "redline_recommendation": (
            "Taraflar, sözleşme süresince ve sona ermesinden itibaren 3 (üç) yıl boyunca karşı tarafın "
            "gizli bilgilerini üçüncü kişilerle paylaşmamayı ve yalnızca sözleşme amacıyla kullanmayı kabul eder."
        ),
    },
    {
        "id": "kvkk_gdpr",
        "title": "KVKK / GDPR Data Protection",
        "detect_patterns": [
            r"\b(kvkk|6698|ki[şs]isel\s+veri\w*|gdpr|data\s+protection|personal\s+data)\b",
        ],
        "high_risk_patterns": [
            r"(a[çc][ıi]k\s+r[ıi]za\s+olmaks[ıi]z[ıi]n\s+yurt\s*d[ıi][şs][ıi]na|without\s+consent\s+transfer\s+to\s+third\s+parties|kvkk\s+sorumlulu[ğg]u\s+tamamen\s+yükleniciye)",
        ],
        "medium_risk_patterns": [
            r"(veri\s+i[şs]leyen\s+t[üu]m\s+cezalardan\s+sorumludur)",
        ],
        "essential": True,
        "redline_recommendation": (
            "Taraflar, 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) ve ilgili mevzuata tam uyum "
            "sağlamayı, kişisel verileri yalnızca hukuka uygun amaçlarla işlemeyi ve teknik/idari güvenlik "
            "tedbirlerini almayı taahhüt eder."
        ),
    },
    {
        "id": "force_majeure",
        "title": "Force Majeure / Mucbir Sebep",
        "detect_patterns": [
            r"\b(m[üu]cbir\s+sebep|force\s+majeure|do[ğg]al\s+afet|salg[ıi]n|sava[şs])\b",
        ],
        "high_risk_patterns": [
            r"(m[üu]cbir\s+sebep\s+kabul\s+edilmez|no\s+force\s+majeure\s+defense|m[üu]cbir\s+sebepte\s+dahi\s+ceza)",
        ],
        "medium_risk_patterns": [
            r"(sadece\s+do[ğg]al\s+afetle\s+s[ıi]n[ıi]rl[ıi]d[ıi]r)",
        ],
        "essential": True,
        "redline_recommendation": (
            "Tarafların kontrolü dışında gelişen doğal afet, salgın hastalık, savaş, siber saldırı ve "
            "resmi makam kararları mücbir sebep sayılır; bu sürede yükümlülükler askıya alınır ve gecikme "
            "cezası uygulanmaz."
        ),
    },
    {
        "id": "payment_terms",
        "title": "Payment Terms / Odeme Vadesi",
        "detect_patterns": [
            r"\b([öo]deme\s+vade\w*|fatura|[öo]deme\s+ko[şs]ul\w*|payment\s+terms|invoice|net\s+\d+\s+days)\b",
        ],
        "high_risk_patterns": [
            r"((?:120|150|180|360)\s+g[üu]n\s+vade|net\s+(?:120|150|180)\s+days|belirsiz\s+vade|tahsilata\s+ba[ğg]l[ıi]\s+[öo]deme|pay\s+when\s+paid)",
        ],
        "medium_risk_patterns": [
            r"((?:60|75|90)\s+g[üu]n\s+vade|net\s+(?:60|75|90)\s+days)",
        ],
        "essential": True,
        "redline_recommendation": (
            "Ödemeler, faturanın tebliğinden itibaren en geç 30 (otuz) takvim günü içinde banka havalesi/EFT "
            "yoluyla yapılır. Vadesinde ödenmeyen tutarlara TCMB ticari temerrüt faizi uygulanır."
        ),
    },
]


def analyze_legal_contract(text: str) -> dict[str, Any]:
    """Scan a Turkish/English contract for critical clauses, assign risk levels, flag missing protective clauses, and generate redline counter-clauses."""
    cleaned_text = (text or "").strip()
    clauses_found: list[dict[str, Any]] = []
    missing_clauses: list[str] = []
    redline_recommendations: list[dict[str, str]] = []

    risk_weights = {"HIGH": 30, "MEDIUM": 15, "LOW": 0}
    total_risk_points = 0

    paragraphs = [p.strip() for p in re.split(r"\n+|[.;]\s+", cleaned_text) if p.strip()]

    for spec in _CLAUSE_CATALOG:
        cid = spec["id"]
        title = spec["title"]
        matched_snippets: list[str] = []

        for para in paragraphs:
            if any(re.search(pat, para, flags=re.IGNORECASE) for pat in spec["detect_patterns"]):
                matched_snippets.append(para)

        if not matched_snippets:
            if spec["essential"]:
                missing_clauses.append(cid)
                total_risk_points += 12
                redline_recommendations.append(
                    {
                        "clause_id": cid,
                        "title": title,
                        "reason": "Missing protective clause in contract",
                        "recommended_text": spec["redline_recommendation"],
                    }
                )
            continue

        joined_match = " ".join(matched_snippets)
        risk_level = "LOW"
        if any(re.search(pat, joined_match, flags=re.IGNORECASE) for pat in spec["high_risk_patterns"]):
            risk_level = "HIGH"
        elif any(re.search(pat, joined_match, flags=re.IGNORECASE) for pat in spec["medium_risk_patterns"]):
            risk_level = "MEDIUM"

        total_risk_points += risk_weights[risk_level]

        clauses_found.append(
            {
                "clause_id": cid,
                "title": title,
                "risk_level": risk_level,
                "excerpt": matched_snippets[0][:280],
                "recommended_redline": spec["redline_recommendation"] if risk_level in ("HIGH", "MEDIUM") else "",
            }
        )

        if risk_level in ("HIGH", "MEDIUM"):
            redline_recommendations.append(
                {
                    "clause_id": cid,
                    "title": title,
                    "reason": f"Detected {risk_level} risk wording in existing clause",
                    "recommended_text": spec["redline_recommendation"],
                }
            )

    high_count = sum(1 for c in clauses_found if c["risk_level"] == "HIGH")
    medium_count = sum(1 for c in clauses_found if c["risk_level"] == "MEDIUM")

    if high_count >= 1 or total_risk_points >= 45:
        overall_risk = "HIGH"
    elif medium_count >= 1 or len(missing_clauses) >= 2 or total_risk_points >= 20:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    risk_score_numeric = min(100, total_risk_points)

    return {
        "overall_risk": overall_risk,
        "risk_score": risk_score_numeric,
        "clauses": clauses_found,
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "missing_clauses": missing_clauses,
        "redline_recommendations": redline_recommendations,
    }


# ============================================================================
# 2. CORPORATE FINANCE, CFO RATIO, 5-YEAR DCF VALUATION & MONTE CARLO ENGINE
# ============================================================================


def run_cfo_financial_analysis(
    revenue: float = 10_000_000.0,
    cogs: float = 6_000_000.0,
    ebitda: float = 2_500_000.0,
    net_income: float = 1_400_000.0,
    current_assets: float = 4_000_000.0,
    inventory: float = 1_200_000.0,
    current_liabilities: float = 2_000_000.0,
    total_assets: float = 12_000_000.0,
    total_debt: float = 3_500_000.0,
    total_equity: float = 6_500_000.0,
    initial_fcf: float | None = None,
    growth_rate: float = 0.12,
    wacc: float = 0.10,
    terminal_growth_rate: float = 0.03,
    initial_investment: float = 5_000_000.0,
    growth_volatility: float = 0.04,
    wacc_volatility: float = 0.015,
    monte_carlo_runs: int = 500,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Compute CFO liquidity/profitability/leverage ratios, 5-Year DCF enterprise valuation, and a 500-run NumPy Monte Carlo NPV simulation."""
    safe_rev = max(1e-9, float(revenue))
    safe_cl = max(1e-9, float(current_liabilities))
    safe_eq = max(1e-9, float(total_equity))
    safe_ta = max(1e-9, float(total_assets))

    current_ratio = round(float(current_assets) / safe_cl, 4)
    quick_ratio = round((float(current_assets) - float(inventory)) / safe_cl, 4)
    gross_profit = float(revenue) - float(cogs)
    gross_margin = round(gross_profit / safe_rev, 4)
    ebitda_margin = round(float(ebitda) / safe_rev, 4)
    roe = round(float(net_income) / safe_eq, 4)
    roa = round(float(net_income) / safe_ta, 4)
    debt_to_equity = round(float(total_debt) / safe_eq, 4)

    base_fcf = float(initial_fcf) if initial_fcf is not None else float(ebitda) * 0.65
    effective_wacc = max(float(wacc), float(terminal_growth_rate) + 0.01)

    projected_fcfs: list[float] = []
    discounted_fcfs: list[float] = []
    for yr in range(1, 6):
        fcf_t = base_fcf * ((1.0 + float(growth_rate)) ** yr)
        pv_t = fcf_t / ((1.0 + effective_wacc) ** yr)
        projected_fcfs.append(round(fcf_t, 2))
        discounted_fcfs.append(round(pv_t, 2))

    pv_of_fcfs = float(sum(discounted_fcfs))
    terminal_fcf = projected_fcfs[-1] * (1.0 + float(terminal_growth_rate))
    terminal_value = terminal_fcf / (effective_wacc - float(terminal_growth_rate))
    pv_terminal_value = terminal_value / ((1.0 + effective_wacc) ** 5)
    enterprise_value = pv_of_fcfs + pv_terminal_value
    base_npv = enterprise_value - float(initial_investment)

    # 500-run NumPy Monte Carlo NPV risk simulation
    runs = max(100, int(monte_carlo_runs))
    rng = np.random.default_rng(random_seed)
    sim_growth = rng.normal(loc=float(growth_rate), scale=max(1e-6, float(growth_volatility)), size=(runs, 5))
    sim_wacc = np.clip(
        rng.normal(loc=effective_wacc, scale=max(1e-6, float(wacc_volatility)), size=runs),
        float(terminal_growth_rate) + 0.008,
        0.50,
    )

    cum_growth = np.cumprod(1.0 + sim_growth, axis=1)
    sim_fcfs = base_fcf * cum_growth
    years_arr = np.arange(1, 6, dtype=np.float64)
    discount_factors = (1.0 + sim_wacc[:, None]) ** years_arr[None, :]
    pv_fcfs_sim = np.sum(sim_fcfs / discount_factors, axis=1)

    term_fcf_sim = sim_fcfs[:, -1] * (1.0 + float(terminal_growth_rate))
    term_val_sim = term_fcf_sim / (sim_wacc - float(terminal_growth_rate))
    pv_term_sim = term_val_sim / ((1.0 + sim_wacc) ** 5)

    ev_sim = pv_fcfs_sim + pv_term_sim
    npv_sim = ev_sim - float(initial_investment)

    p10, p50, p90 = np.percentile(npv_sim, [10, 50, 90])
    prob_positive_npv = float(np.mean(npv_sim > 0.0))

    return {
        "ratios": {
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "gross_margin": gross_margin,
            "ebitda_margin": ebitda_margin,
            "roe": roe,
            "roa": roa,
            "debt_to_equity": debt_to_equity,
        },
        "dcf": {
            "base_fcf": round(base_fcf, 2),
            "wacc": round(effective_wacc, 4),
            "terminal_growth_rate": round(float(terminal_growth_rate), 4),
            "projected_fcfs": projected_fcfs,
            "discounted_fcfs": discounted_fcfs,
            "pv_of_fcfs": round(pv_of_fcfs, 2),
            "terminal_value": round(terminal_value, 2),
            "pv_terminal_value": round(pv_terminal_value, 2),
            "enterprise_value": round(enterprise_value, 2),
            "base_npv": round(base_npv, 2),
        },
        "monte_carlo": {
            "runs": runs,
            "p10_npv": round(float(p10), 2),
            "p50_npv": round(float(p50), 2),
            "p90_npv": round(float(p90), 2),
            "mean_npv": round(float(np.mean(npv_sim)), 2),
            "std_npv": round(float(np.std(npv_sim)), 2),
            "prob_positive_npv": round(prob_positive_npv, 4),
        },
    }


# ============================================================================
# 3. ACADEMIC RESEARCH & TAGUCHI DESIGN OF EXPERIMENTS (DoE)
# ============================================================================

_TAGUCHI_L4: list[list[int]] = [
    [0, 0, 0],
    [0, 1, 1],
    [1, 0, 1],
    [1, 1, 0],
]

_TAGUCHI_L8: list[list[int]] = [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 1, 1],
    [0, 1, 1, 0, 0, 1, 1],
    [0, 1, 1, 1, 1, 0, 0],
    [1, 0, 1, 0, 1, 0, 1],
    [1, 0, 1, 1, 0, 1, 0],
    [1, 1, 0, 0, 1, 1, 0],
    [1, 1, 0, 1, 0, 0, 1],
]

_TAGUCHI_L9: list[list[int]] = [
    [0, 0, 0, 0],
    [0, 1, 1, 1],
    [0, 2, 2, 2],
    [1, 0, 1, 2],
    [1, 1, 2, 0],
    [1, 2, 0, 1],
    [2, 0, 2, 1],
    [2, 1, 0, 2],
    [2, 2, 1, 0],
]


def compute_taguchi_sn_ratio(observations: list[float], mode: str = "smaller-is-better") -> float:
    """Compute Taguchi Signal-to-Noise (S/N) ratio in dB for a trial's observations."""
    arr = np.asarray(observations, dtype=np.float64)
    if arr.size == 0:
        raise ValueError("observations must not be empty")
    n = float(arr.size)
    mode_norm = mode.strip().lower().replace("_", "-")

    if mode_norm == "smaller-is-better":
        mse = float(np.sum(arr**2)) / n
        return round(-10.0 * math.log10(max(mse, 1e-12)), 4)

    if mode_norm == "larger-is-better":
        safe_arr = np.where(np.abs(arr) < 1e-12, 1e-12, arr)
        mean_inv_sq = float(np.sum(1.0 / (safe_arr**2))) / n
        return round(-10.0 * math.log10(max(mean_inv_sq, 1e-12)), 4)

    if mode_norm == "nominal-is-best":
        mean_val = float(np.mean(arr))
        var_val = float(np.var(arr, ddof=1)) if arr.size > 1 else max(1e-9, (0.01 * mean_val) ** 2)
        ratio = (mean_val**2) / max(var_val, 1e-12)
        return round(10.0 * math.log10(max(ratio, 1e-12)), 4)

    raise ValueError(f"Unsupported Taguchi S/N mode: {mode}")


def format_academic_citation(
    authors: list[str],
    year: int,
    title: str,
    journal: str,
    volume: int | str = 1,
    pages: str = "1-12",
    index: int = 1,
) -> dict[str, str]:
    """Format an academic reference in both APA 7th and IEEE styles."""
    clean_authors = [a.strip() for a in authors if a.strip()] or ["Anonim, A."]
    apa_authors = ", ".join(clean_authors)
    ieee_authors = ", ".join(clean_authors)
    apa = f"{apa_authors} ({year}). {title}. {journal}, {volume}, {pages}."
    ieee = f"[{index}] {ieee_authors}, \"{title},\" {journal}, vol. {volume}, pp. {pages}, {year}."
    return {"apa": apa, "ieee": ieee}


def generate_taguchi_doe(
    factors: dict[str, list[Any]],
    responses: list[list[float]] | list[float] | None = None,
    objective: str = "smaller-is-better",
    citation_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an Orthogonal Array experimental design matrix (L4 / L8 / L9), compute Signal-to-Noise (S/N) ratios, and format APA/IEEE citations."""
    if not factors:
        raise ValueError("factors dictionary must contain at least one factor")

    factor_names = list(factors.keys())
    max_levels = max(len(v) for v in factors.values())
    num_factors = len(factor_names)

    if max_levels >= 3:
        array_name = "L9"
        base_oa = _TAGUCHI_L9
    elif num_factors <= 3:
        array_name = "L4"
        base_oa = _TAGUCHI_L4
    else:
        array_name = "L8"
        base_oa = _TAGUCHI_L8

    experiments: list[dict[str, Any]] = []
    for run_idx, row in enumerate(base_oa, start=1):
        factor_assignment: dict[str, Any] = {}
        level_indices: dict[str, int] = {}
        for col_idx, fname in enumerate(factor_names):
            levels = factors[fname]
            lvl_pos = row[col_idx % len(row)] % len(levels)
            factor_assignment[fname] = levels[lvl_pos]
            level_indices[fname] = lvl_pos + 1

        experiments.append(
            {
                "run": run_idx,
                "levels": level_indices,
                "factors": factor_assignment,
            }
        )

    # Compute S/N ratios across all three objectives and the selected primary objective
    sn_results: list[dict[str, Any]] = []
    for idx, exp in enumerate(experiments):
        if responses is not None and idx < len(responses):
            raw_obs = responses[idx]
            obs_list = [float(x) for x in raw_obs] if isinstance(raw_obs, (list, tuple)) else [float(raw_obs)]
        else:
            # Deterministic synthetic observations derived from numeric factor values or run index
            numeric_vals = [float(v) for v in exp["factors"].values() if isinstance(v, (int, float))]
            base_val = sum(numeric_vals) / len(numeric_vals) if numeric_vals else float(idx + 1) * 10.0
            obs_list = [round(base_val * 0.98, 4), round(base_val * 1.00, 4), round(base_val * 1.02, 4)]

        sn_smaller = compute_taguchi_sn_ratio(obs_list, "smaller-is-better")
        sn_larger = compute_taguchi_sn_ratio(obs_list, "larger-is-better")
        sn_nominal = compute_taguchi_sn_ratio(obs_list, "nominal-is-best")
        sn_primary = compute_taguchi_sn_ratio(obs_list, objective)

        exp["observations"] = obs_list
        exp["sn_ratio_db"] = sn_primary
        exp["sn_breakdown"] = {
            "smaller_is_better": sn_smaller,
            "larger_is_better": sn_larger,
            "nominal_is_best": sn_nominal,
        }
        sn_results.append({"run": exp["run"], "sn_ratio_db": sn_primary})

    best_run = max(experiments, key=lambda e: e["sn_ratio_db"])

    meta = citation_meta or {}
    citations = format_academic_citation(
        authors=meta.get("authors", ["Taguchi, G.", "Phadke, M. S."]),
        year=int(meta.get("year", 1989)),
        title=meta.get("title", "Quality Engineering Using Robust Design"),
        journal=meta.get("journal", "IEEE Transactions on Reliability"),
        volume=meta.get("volume", 38),
        pages=meta.get("pages", "145-158"),
        index=int(meta.get("index", 1)),
    )

    return {
        "orthogonal_array": array_name,
        "num_factors": num_factors,
        "num_runs": len(experiments),
        "objective": objective,
        "experiments": experiments,
        "optimal_run": {
            "run": best_run["run"],
            "factors": best_run["factors"],
            "sn_ratio_db": best_run["sn_ratio_db"],
        },
        "citations": citations,
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


def _translate_natural_query_to_sql(natural_query: str, schema: dict[str, Any]) -> str:
    """Deterministically translate a Turkish/English natural language query into a safe SELECT query."""
    tables: list[dict[str, Any]] = schema.get("tables", [])
    if not tables:
        raise ValueError("Database contains no user tables to query")

    q_lower = (natural_query or "").lower()

    # Pick target table mentioned in natural query, or default to first table
    target_table = tables[0]
    for tbl in tables:
        tname = tbl["name"].lower()
        tname_singular = tname.rstrip("s")
        if tname in q_lower or (len(tname_singular) >= 3 and tname_singular in q_lower):
            target_table = tbl
            break

    t_name = target_table["name"]
    col_names = [c["name"] for c in target_table["columns"]]
    numeric_cols = [
        c["name"]
        for c in target_table["columns"]
        if any(k in (c["type"] or "").upper() for k in ("INT", "REAL", "NUM", "DEC", "FLOAT", "DOUBLE"))
        and not c["pk"]
    ]

    import sql_safe

    # Check if user asked for count
    if any(k in q_lower for k in ("kaç", "kac", "sayısı", "sayisi", "count", "how many", "toplam kayıt")):
        return sql_safe.build_select(t_name, "COUNT(*) AS total_count")

    # Check if user asked for sum / average
    if any(k in q_lower for k in ("toplam", "sum", "total")) and numeric_cols:
        target_col = numeric_cols[0]
        for nc in numeric_cols:
            if nc.lower() in q_lower:
                target_col = nc
                break
        q_col = sql_safe.safe_ident(target_col)
        return sql_safe.build_select(t_name, f"SUM({q_col}) AS total_{target_col}, COUNT(*) AS row_count")

    if any(k in q_lower for k in ("ortalama", "average", "avg", "mean")) and numeric_cols:
        target_col = numeric_cols[0]
        for nc in numeric_cols:
            if nc.lower() in q_lower:
                target_col = nc
                break
        q_col = sql_safe.safe_ident(target_col)
        return sql_safe.build_select(t_name, f"AVG({q_col}) AS avg_{target_col}, COUNT(*) AS row_count")

    # Ordering and limit heuristics
    order_clause = ""
    if any(k in q_lower for k in ("en yüksek", "en buyuk", "en büyük", "top", "highest", "most", "descending")):
        sort_col = numeric_cols[0] if numeric_cols else col_names[0]
        for c in col_names:
            if c.lower() in q_lower:
                sort_col = c
                break
        order_clause = f"{sql_safe.safe_ident(sort_col)} DESC"

    limit_val = 50
    m_lim = re.search(r"\b(?:ilk|top|limit)\s+(\d{1,4})\b", q_lower)
    if m_lim:
        limit_val = min(500, max(1, int(m_lim.group(1))))

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

            tables_meta.append(
                {
                    "name": tname,
                    "columns": cols_list,
                    "foreign_keys": fks_list,
                }
            )

        schema_info = {"tables": tables_meta, "relationships": relationships}
        raw_sql = sql_override if sql_override is not None else _translate_natural_query_to_sql(natural_query, schema_info)
        safe_sql = _validate_readonly_select(raw_sql)

        cur.execute(safe_sql)
        fetched = cur.fetchall()
        rows = [dict(r) for r in fetched]
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
