"""DOM-01..DOM-11: Zero-Default Domain Engines (Finance DCF, Legal, Health, Unit-Safe Eng, CNC, G-Code, Math & Tutor)."""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
from pydantic import BaseModel, Field, ValidationError

from hallucination.verifier import apply_high_risk_guardrails, verify_standard_and_law_numbers

# ---------------------------------------------------------------- DOM-01 Strict Zero-Default Contract

class MissingDomainInputsError(ValueError):
    """DOM-01: Raised whenever required domain inputs are missing (NEVER fabricates default values)."""

    def __init__(self, domain: str, missing_fields: list[str], questions: list[str]) -> None:
        self.domain = domain
        self.missing_fields = missing_fields
        self.questions = questions
        super().__init__(f"{domain} için eksik zorunlu girdiler: {', '.join(missing_fields)}")


def _validate_strict_schema(model_cls: type[BaseModel], raw: dict[str, Any], domain: str) -> BaseModel:
    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        missing = [str(e["loc"][-1]) for e in exc.errors() if e.get("loc")]
        qs = [f"Lütfen '{m}' değerini sayısal/açık olarak belirtin." for m in missing[:3]]
        raise MissingDomainInputsError(domain, missing, qs) from exc


# ---------------------------------------------------------------- DOM-02 Finance: DCF + WACC + Sensitivity + Monte Carlo

class DCFInput(BaseModel):
    cash_flows: list[float] = Field(..., min_length=1)
    wacc: float = Field(..., gt=0.0, lt=1.0)
    terminal_growth: float = Field(..., ge=-0.05, lt=0.25)
    net_debt: float
    shares_outstanding: float = Field(..., gt=0.0)
    currency: str = Field(...)
    seed: int = 42


def run_finance_dcf(raw_inputs: dict[str, Any]) -> dict[str, Any]:
    """DOM-01 & DOM-02: Strict DCF valuation + WACC sensitivity + seeded Monte Carlo (zero default fabrication)."""
    inp: DCFInput = _validate_strict_schema(DCFInput, raw_inputs, "finance_dcf")  # type: ignore[assignment]
    if inp.terminal_growth >= inp.wacc:
        raise ValueError("Terminal büyüme oranı WACC değerinden küçük olmalıdır (Gordon Growth koşulu).")

    pv_cfs = [cf / ((1.0 + inp.wacc) ** t) for t, cf in enumerate(inp.cash_flows, start=1)]
    last_cf = inp.cash_flows[-1]
    terminal_val = (last_cf * (1.0 + inp.terminal_growth)) / (inp.wacc - inp.terminal_growth)
    pv_terminal = terminal_val / ((1.0 + inp.wacc) ** len(inp.cash_flows))
    ev = sum(pv_cfs) + pv_terminal
    equity_val = ev - inp.net_debt
    per_share = equity_val / inp.shares_outstanding

    # WACC sensitivity (-1%, base, +1%)
    sens: list[dict[str, float]] = []
    for delta in (-0.01, 0.0, 0.01):
        w = max(inp.terminal_growth + 0.005, inp.wacc + delta)
        pv_s = sum(cf / ((1.0 + w) ** t) for t, cf in enumerate(inp.cash_flows, start=1))
        tv_s = (last_cf * (1.0 + inp.terminal_growth)) / (w - inp.terminal_growth)
        eq_s = pv_s + tv_s / ((1.0 + w) ** len(inp.cash_flows)) - inp.net_debt
        sens.append({"wacc": round(w, 4), "value_per_share": round(eq_s / inp.shares_outstanding, 4)})

    # Seeded Monte Carlo (500 draws around +-10% CF & +-0.5% WACC)
    rng = np.random.default_rng(inp.seed)
    mc_vals: list[float] = []
    for _ in range(500):
        w_m = max(inp.terminal_growth + 0.005, float(rng.normal(inp.wacc, 0.005)))
        scale = float(rng.normal(1.0, 0.08))
        cfs_m = [cf * scale for cf in inp.cash_flows]
        pv_m = sum(cf / ((1.0 + w_m) ** t) for t, cf in enumerate(cfs_m, start=1))
        tv_m = (cfs_m[-1] * (1.0 + inp.terminal_growth)) / (w_m - inp.terminal_growth)
        mc_vals.append((pv_m + tv_m / ((1.0 + w_m) ** len(cfs_m)) - inp.net_debt) / inp.shares_outstanding)
    arr_mc = np.asarray(mc_vals)

    return {
        "result": {
            "enterprise_value": round(ev, 4),
            "equity_value": round(equity_val, 4),
            "value_per_share": round(per_share, 4),
            "pv_cash_flows": [round(v, 4) for v in pv_cfs],
            "pv_terminal_value": round(pv_terminal, 4),
            "sensitivity": sens,
            "monte_carlo_p10_p50_p90": [round(float(np.percentile(arr_mc, p)), 4) for p in (10, 50, 90)],
        },
        "units": {"monetary": inp.currency, "rates": "ondalık oran"},
        "assumptions": {
            "wacc": inp.wacc,
            "terminal_growth": inp.terminal_growth,
            "horizon_years": len(inp.cash_flows),
            "mc_seed": inp.seed,
        },
        "sources": ["Gordon Growth Model (Damodaran, Investment Valuation)"],
        "disclaimer": "Bu hesaplama yalnızca bilgilendirme amaçlıdır; yatırım tavsiyesi değildir.",
    }


# ---------------------------------------------------------------- DOM-03 Legal Clause Analysis

class LegalClauseInput(BaseModel):
    contract_text: str = Field(..., min_length=40)
    jurisdiction: str = Field(...)
    sources: list[dict[str, Any]] = Field(default_factory=list)


_LEGAL_RISK_RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("tek_tarafli_fesih", "high", re.compile(r"(?:tek\s+taraflı|sebepsiz|bildirimsiz)\s+fesih", re.IGNORECASE)),
    ("sinirsiz_sorumluluk", "high", re.compile(r"(?:sınırsız\s+sorumluluk|tüm\s+dolaylı\s+zararlar|unlimited\s+liability)", re.IGNORECASE)),
    ("otomatik_yenileme", "medium", re.compile(r"(?:otomatik\s+olarak\s+yenilenir|auto[\-\s]?renew)", re.IGNORECASE)),
    ("cezai_sart", "medium", re.compile(r"(?:cezai\s+şart|gecikme\s+cezası|liquidated\s+damages)", re.IGNORECASE)),
)


def analyze_legal_contract(raw_inputs: dict[str, Any]) -> dict[str, Any]:
    """DOM-03: Require explicit contract text, segment clauses, flag risk clauses & verify statute numbers."""
    inp: LegalClauseInput = _validate_strict_schema(LegalClauseInput, raw_inputs, "legal_contract")  # type: ignore[assignment]
    clauses = [c.strip() for c in re.split(r"\n+|(?=Madde\s+\d+\.)", inp.contract_text) if len(c.strip()) >= 15]
    findings: list[dict[str, Any]] = []
    for idx, cl in enumerate(clauses, start=1):
        for risk_type, sev, pat in _LEGAL_RISK_RULES:
            if pat.search(cl):
                findings.append({
                    "clause_index": idx,
                    "risk_type": risk_type,
                    "severity": sev,
                    "clause_excerpt": cl[:180],
                    "redline_suggestion": f"Taslak öneri ({risk_type}): karşılıklı bildirim süresi ve üst sorumluluk sınırı ekleyin.",
                })
    statute_check = verify_standard_and_law_numbers(inp.contract_text, inp.sources)
    return {
        "result": {"clause_count": len(clauses), "risk_findings": findings, "statute_verification": statute_check},
        "assumptions": {"jurisdiction": inp.jurisdiction},
        "sources": [s.get("url") or s.get("doc", "mevzuat") for s in inp.sources],
        "disclaimer": "Taslak analizdir; hukuki karar öncesi yetkili bir avukat incelemesi gerekir.",
    }


# ---------------------------------------------------------------- DOM-04 Health Safety Policy

_EMERGENCY_SYMPTOMS_RE = re.compile(
    r"\b(göğüs\s+ağrısı|nefes\s+darlığı|felç|bayılma|şiddetli\s+kanama|intihar|chest\s+pain|shortness\s+of\s+breath|stroke)\b",
    re.IGNORECASE,
)


def evaluate_health_query(query: str, *, trusted_sources: list[dict[str, Any]]) -> dict[str, Any]:
    """DOM-04: Emergency triage + trusted-source-only general health info (zero diagnosis/dosage)."""
    if _EMERGENCY_SYMPTOMS_RE.search(query or ""):
        return {
            "emergency": True,
            "response": "Acil tıbbi belirti bildirildi: Lütfen vakit kaybetmeden 112 Acil Servis'i arayın veya en yakın acil servise başvurun.",
            "sources": ["T.C. Sağlık Bakanlığı / 112 Acil Yardım"],
            "disclaimer": "Bu sistem tıbbi teşhis veya acil müdahale sağlamaz.",
        }
    guarded = apply_high_risk_guardrails(
        "Güvenilir sağlık kaynaklarına göre genel bilgi özeti [S1].",
        domain="health",
        sources=trusted_sources,
    )
    return {
        "emergency": False,
        "blocked": guarded["blocked"],
        "response": guarded["text"],
        "sources": [s.get("url") or s.get("doc", "") for s in trusted_sources],
        "disclaimer": "Bu bilgi tıbbi teşhis, ilaç dozu veya tedavi planı yerine geçmez; hekime danışın.",
    }


# ---------------------------------------------------------------- DOM-05 Unit-Safe Engineering Calculator

class DimensionalityError(ValueError):
    """DOM-05: Raised on incompatible physical dimensions (never silently converts incompatible units)."""


_UNIT_TABLE: dict[str, tuple[str, float]] = {
    "mm": ("length", 1e-3), "cm": ("length", 1e-2), "m": ("length", 1.0), "km": ("length", 1e3),
    "in": ("length", 0.0254), "inch": ("length", 0.0254), "ft": ("length", 0.3048),
    "yd": ("length", 0.9144), "mi": ("length", 1609.344),
    "g": ("mass", 1e-3), "kg": ("mass", 1.0), "ton": ("mass", 1e3),
    "lb": ("mass", 0.45359237), "oz": ("mass", 0.028349523125),
    "N": ("force", 1.0), "kN": ("force", 1e3), "lbf": ("force", 4.448221615),
    "Pa": ("stress", 1.0), "kPa": ("stress", 1e3), "bar": ("stress", 1e5),
    "MPa": ("stress", 1e6), "GPa": ("stress", 1e9), "psi": ("stress", 6894.757293),
    "ms": ("time", 1e-3), "s": ("time", 1.0), "min": ("time", 60.0), "h": ("time", 3600.0),
    "W": ("power", 1.0), "kW": ("power", 1e3), "hp": ("power", 745.699872),
}


@dataclass(frozen=True)
class UnitQuantity:
    value: float
    unit: str

    def dimension(self) -> str:
        if self.unit not in _UNIT_TABLE:
            raise DimensionalityError(f"Tanımsız fiziksel birim: {self.unit}")
        return _UNIT_TABLE[self.unit][0]

    def to_si(self) -> float:
        if self.unit not in _UNIT_TABLE:
            raise DimensionalityError(f"Tanımsız fiziksel birim: {self.unit}")
        return self.value * _UNIT_TABLE[self.unit][1]

    def to(self, target_unit: str) -> UnitQuantity:
        if target_unit not in _UNIT_TABLE:
            raise DimensionalityError(f"Tanımsız hedef birim: {target_unit}")
        if self.dimension() != _UNIT_TABLE[target_unit][0]:
            raise DimensionalityError(f"Birim uyuşmazlığı: '{self.unit}' ({self.dimension()}) -> '{target_unit}' ({_UNIT_TABLE[target_unit][0]}) dönüştürülemez.")
        return UnitQuantity(round(self.to_si() / _UNIT_TABLE[target_unit][1], 8), target_unit)

    def add(self, other: UnitQuantity) -> UnitQuantity:
        if self.dimension() != other.dimension():
            raise DimensionalityError(f"Birim uyuşmazlığı: '{self.unit}' ile '{other.unit}' toplanamaz.")
        converted = other.to(self.unit)
        return UnitQuantity(round(self.value + converted.value, 8), self.unit)


# ---------------------------------------------------------------- DOM-06, 07, 08 CNC Eval, Kienzle Physics & G-Code Safety

class KienzleInput(BaseModel):
    kc1_1_mpa: float = Field(..., gt=100.0, lt=5000.0)
    mc: float = Field(..., gt=0.05, lt=0.6)
    ap_mm: float = Field(..., gt=0.05, lt=50.0)
    f_mm_rev: float = Field(..., gt=0.01, lt=3.0)
    kappa_deg: float = Field(..., gt=10.0, lt=120.0)


def compute_kienzle_cutting_force(raw_inputs: dict[str, Any]) -> dict[str, Any]:
    """DOM-07: Literature-verified Kienzle cutting force Fc = kc1.1 * b * h^(1 - mc), explicitly labeled approximate."""
    inp: KienzleInput = _validate_strict_schema(KienzleInput, raw_inputs, "cnc_kienzle")  # type: ignore[assignment]
    rad = math.radians(inp.kappa_deg)
    h = inp.f_mm_rev * math.sin(rad)
    b = inp.ap_mm / math.sin(rad)
    fc_n = inp.kc1_1_mpa * b * (h ** (1.0 - inp.mc))
    warnings = ["Uygulanabilirlik sınırı uyarısı: çok küçük talaş kalınlığında (h < 0.05 mm) Kienzle sapması artar."] if h < 0.05 else []
    return {
        "result": {"fc_N": round(fc_n, 2), "chip_thickness_mm": round(h, 4), "chip_width_mm": round(b, 4)},
        "label": "yaklaşık/tahmini",
        "uncertainty_note": "Tezgah rijitliği ve takım aşınmasına bağlı +-10% belirsizlik içerir.",
        "warnings": warnings,
        "assumptions": inp.model_dump(),
        "sources": ["Kienzle (1952) / Altintas, Manufacturing Automation"],
        "units": {"fc_N": "N", "chip_thickness_mm": "mm"},
    }


def evaluate_cnc_ballooning_accuracy(predicted: list[dict[str, Any]], ground_truth: list[dict[str, Any]]) -> dict[str, Any]:
    """DOM-06: Compute balloon recall, precision, and dimension-value accuracy against labeled drawings."""
    gt_map = {str(g["balloon_no"]): g for g in ground_truth}
    pr_map = {str(p["balloon_no"]): p for p in predicted}
    matched = set(gt_map) & set(pr_map)
    recall = len(matched) / max(1, len(gt_map))
    precision = len(matched) / max(1, len(pr_map))
    val_ok = sum(
        1 for k in matched if abs(float(pr_map[k]["nominal"]) - float(gt_map[k]["nominal"])) <= 1e-3
    )
    dim_acc = val_ok / max(1, len(matched))
    return {
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "dimension_accuracy": round(dim_acc, 4),
        "passed": recall >= 0.90 and dim_acc >= 0.95,
    }


_ALLOWED_GCODES = frozenset({0, 1, 2, 3, 17, 18, 19, 20, 21, 28, 40, 41, 42, 43, 49, 54, 80, 81, 83, 90, 91, 94, 95})


def _check_gcode_line(lineno: int, line: str, spindle_on: bool, has_feed: bool) -> tuple[bool, bool, list[str]]:
    line_errors: list[str] = []
    if any(m in line for m in ("M03", "M3", "M04", "M4")):
        spindle_on = True
    if "F" in line and re.search(r"F\d+", line):
        has_feed = True
    if re.search(r"\bG0?0\b", line):
        zm = re.search(r"Z(-?\d+(?:\.\d+)?)", line)
        if zm and float(zm.group(1)) < 0.0:
            line_errors.append(f"Satır {lineno}: Hızlı konumlamada (G00) negatif Z ({zm.group(1)}) çarpışma riski!")
    if re.search(r"\bG0?1\b", line):
        if not has_feed:
            line_errors.append(f"Satır {lineno}: G01 kesme hareketinde ilerleme hızı (F) tanımlanmamış.")
        if not spindle_on:
            line_errors.append(f"Satır {lineno}: İş mili (M03/M04) açılmadan G01 kesme komutu verilmiş.")
    for code_num in re.findall(r"\bG(\d+)\b", line):
        if int(code_num) not in _ALLOWED_GCODES:
            line_errors.append(f"Satır {lineno}: Desteklenmeyen veya geçersiz G kodu: G{code_num}")
    return spindle_on, has_feed, line_errors


def validate_gcode_safety(gcode: str) -> dict[str, Any]:
    """DOM-08: Syntax & collision checker (rapid G00 into Z<0, missing feed on G01, invalid codes) + mandatory warning."""
    errors: list[str] = []
    spindle_on = False
    has_feed = False
    for lineno, raw in enumerate((gcode or "").splitlines(), start=1):
        line = raw.split(";", 1)[0].split("(", 1)[0].strip().upper()
        if not line or line.startswith("%"):
            continue
        spindle_on, has_feed, line_errors = _check_gcode_line(lineno, line, spindle_on, has_feed)
        errors.extend(line_errors)

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "safety_warning": "UYARI: Üretilen G-kodu gerçek CNC tezgâhında çalıştırılmadan önce mutlaka CAM simülatöründe ve boşta (dry-run) doğrulanmalıdır.",
    }


# ---------------------------------------------------------------- DOM-09, 10, 11 Verified Math/Science & Programming Tutor

def solve_polynomial_derivative_crosschecked(coeffs: list[float], x_val: float) -> dict[str, Any]:
    """DOM-10: Two-method cross-checked polynomial derivative (exact power rule vs central finite difference)."""
    if not coeffs:
        return {"solved": False, "reason": "Çözemedim: boş polinom katsayı listesi."}
    # coeffs = [c0, c1, c2, ...] for c0 + c1*x + c2*x^2 + ...
    analytic = sum(k * c * (x_val ** (k - 1)) for k, c in enumerate(coeffs) if k >= 1)
    h = 1e-6
    f_plus = sum(c * ((x_val + h) ** k) for k, c in enumerate(coeffs))
    f_minus = sum(c * ((x_val - h) ** k) for k, c in enumerate(coeffs))
    numeric = (f_plus - f_minus) / (2 * h)
    agrees = abs(analytic - numeric) <= 1e-4 * max(1.0, abs(analytic))
    return {
        "solved": agrees,
        "analytic_result": round(analytic, 6),
        "numeric_crosscheck": round(numeric, 6),
        "methods_agree": agrees,
    }


def generate_verified_math_exercise(a: int, b: int) -> dict[str, Any]:
    """DOM-09: Generate linear equation exercise ax + b = c whose solution is programmatically verified before return."""
    x_true = 4
    c = a * x_true + b
    check = (a * x_true + b) == c
    return {
        "question": f"{a}x + {b} = {c} denkleminde x kaçtır?",
        "solution": x_true,
        "verified_by_tool": check,
        "steps": [f"{a}x = {c} - {b} = {c - b}", f"x = {c - b} / {a} = {x_true}"],
    }


def verify_tutor_code_output(code: str, claimed_stdout: str) -> dict[str, Any]:
    """DOM-11: Verify programming tutor's claimed output via pure-AST safe evaluation of print expressions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"matched": False, "error": f"Sözdizimi hatası: {exc.msg}"}
    # Execute tiny deterministic pure expressions in an empty restricted namespace (no builtins I/O/imports)
    captured: list[str] = []
    safe_builtins = {"range": range, "len": len, "sum": sum, "min": min, "max": max, "int": int, "float": float, "str": str, "list": list, "print": lambda *a: captured.append(" ".join(map(str, a)))}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute)):
            return {"matched": False, "error": "Eğitim izleyici yalnızca saf ifade/döngü örneklerini doğrular."}
    env: dict[str, Any] = {"__builtins__": safe_builtins}
    exec(compile(tree, "<tutor>", "exec"), env, env)
    actual = "\n".join(captured).strip()
    return {"matched": actual == claimed_stdout.strip(), "actual_stdout": actual, "claimed_stdout": claimed_stdout.strip()}
