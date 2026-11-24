"""Helper engines for Domain Experts [M57]: Legal Contract Risk Analyzer & Taguchi DoE / Academic Citations."""

from __future__ import annotations

import math
import re
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

_RISK_WEIGHTS = {"HIGH": 30, "MEDIUM": 15, "LOW": 0}


def _classify_clause_risk(spec: dict[str, Any], joined_match: str) -> str:
    if any(re.search(pat, joined_match, flags=re.IGNORECASE) for pat in spec["high_risk_patterns"]):
        return "HIGH"
    if any(re.search(pat, joined_match, flags=re.IGNORECASE) for pat in spec["medium_risk_patterns"]):
        return "MEDIUM"
    return "LOW"


def _evaluate_clause_spec(
    spec: dict[str, Any],
    paragraphs: list[str],
) -> tuple[dict[str, Any] | None, str | None, dict[str, str] | None, int]:
    cid, title = spec["id"], spec["title"]
    matched = [p for p in paragraphs if any(re.search(pat, p, flags=re.IGNORECASE) for pat in spec["detect_patterns"])]
    if not matched:
        if not spec["essential"]:
            return None, None, None, 0
        rec = {
            "clause_id": cid,
            "title": title,
            "reason": "Missing protective clause in contract",
            "recommended_text": spec["redline_recommendation"],
        }
        return None, cid, rec, 12

    risk_level = _classify_clause_risk(spec, " ".join(matched))
    clause_entry = {
        "clause_id": cid,
        "title": title,
        "risk_level": risk_level,
        "excerpt": matched[0][:280],
        "recommended_redline": spec["redline_recommendation"] if risk_level in ("HIGH", "MEDIUM") else "",
    }
    rec = (
        {
            "clause_id": cid,
            "title": title,
            "reason": f"Detected {risk_level} risk wording in existing clause",
            "recommended_text": spec["redline_recommendation"],
        }
        if risk_level in ("HIGH", "MEDIUM")
        else None
    )
    return clause_entry, None, rec, _RISK_WEIGHTS[risk_level]


def analyze_legal_contract(text: str) -> dict[str, Any]:
    """Scan a Turkish/English contract for critical clauses, assign risk levels, flag missing protective clauses, and generate redline counter-clauses."""
    cleaned_text = (text or "").strip()
    paragraphs = [p.strip() for p in re.split(r"\n+|[.;]\s+", cleaned_text) if p.strip()]

    clauses_found: list[dict[str, Any]] = []
    missing_clauses: list[str] = []
    redline_recommendations: list[dict[str, str]] = []
    total_risk_points = 0

    for spec in _CLAUSE_CATALOG:
        clause_entry, missing_id, rec, points = _evaluate_clause_spec(spec, paragraphs)
        total_risk_points += points
        if clause_entry is not None:
            clauses_found.append(clause_entry)
        if missing_id is not None:
            missing_clauses.append(missing_id)
        if rec is not None:
            redline_recommendations.append(rec)

    high_count = sum(1 for c in clauses_found if c["risk_level"] == "HIGH")
    medium_count = sum(1 for c in clauses_found if c["risk_level"] == "MEDIUM")
    if high_count >= 1 or total_risk_points >= 45:
        overall_risk = "HIGH"
    elif medium_count >= 1 or len(missing_clauses) >= 2 or total_risk_points >= 20:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    return {
        "overall_risk": overall_risk,
        "risk_score": min(100, total_risk_points),
        "clauses": clauses_found,
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "missing_clauses": missing_clauses,
        "redline_recommendations": redline_recommendations,
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


_CITATION_EXTRA_POS = ("volume", "pages", "index")


def format_academic_citation(
    authors: list[str],
    year: int,
    title: str,
    journal: str,
    *args: Any,
    **kwargs: Any,
) -> dict[str, str]:
    """Format an academic reference in both APA 7th and IEEE styles."""
    extra = dict(zip(_CITATION_EXTRA_POS, args, strict=False))
    extra.update(kwargs)
    volume = extra.get("volume", 1)
    pages = str(extra.get("pages", "1-12"))
    index = int(extra.get("index", 1))

    clean_authors = [a.strip() for a in authors if a.strip()] or ["Anonim, A."]
    author_str = ", ".join(clean_authors)
    apa = f"{author_str} ({year}). {title}. {journal}, {volume}, {pages}."
    ieee = f'[{index}] {author_str}, "{title}," {journal}, vol. {volume}, pp. {pages}, {year}.'
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
        array_name, base_oa = "L9", _TAGUCHI_L9
    elif num_factors <= 3:
        array_name, base_oa = "L4", _TAGUCHI_L4
    else:
        array_name, base_oa = "L8", _TAGUCHI_L8

    experiments: list[dict[str, Any]] = []
    for run_idx, row in enumerate(base_oa, start=1):
        factor_assignment: dict[str, Any] = {}
        level_indices: dict[str, int] = {}
        for col_idx, fname in enumerate(factor_names):
            levels = factors[fname]
            lvl_pos = row[col_idx % len(row)] % len(levels)
            factor_assignment[fname] = levels[lvl_pos]
            level_indices[fname] = lvl_pos + 1
        experiments.append({"run": run_idx, "levels": level_indices, "factors": factor_assignment})

    for idx, exp in enumerate(experiments):
        if responses is not None and idx < len(responses):
            raw_obs = responses[idx]
            obs_list = [float(x) for x in raw_obs] if isinstance(raw_obs, (list, tuple)) else [float(raw_obs)]
        else:
            numeric_vals = [float(v) for v in exp["factors"].values() if isinstance(v, (int, float))]
            base_val = sum(numeric_vals) / len(numeric_vals) if numeric_vals else float(idx + 1) * 10.0
            obs_list = [round(base_val * 0.98, 4), round(base_val * 1.00, 4), round(base_val * 1.02, 4)]

        exp["observations"] = obs_list
        exp["sn_ratio_db"] = compute_taguchi_sn_ratio(obs_list, objective)
        exp["sn_breakdown"] = {
            "smaller_is_better": compute_taguchi_sn_ratio(obs_list, "smaller-is-better"),
            "larger_is_better": compute_taguchi_sn_ratio(obs_list, "larger-is-better"),
            "nominal_is_best": compute_taguchi_sn_ratio(obs_list, "nominal-is-best"),
        }

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
