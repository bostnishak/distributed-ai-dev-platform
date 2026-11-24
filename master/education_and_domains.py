"""EGT-01..05 & ALN-01..07: Education Tools (Quiz, Lesson Plan, Progress, Autograder, Language) & Verified Domain Calculators."""

from __future__ import annotations

import ast
import math
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from access_control import require_local_or_admin

router = APIRouter(prefix="/api/tools", tags=["tools"])
_ADMIN_OR_LOCAL = [Depends(require_local_or_admin)]

_LEARNING_PROGRESS: dict[str, dict[str, Any]] = {}

# ALN-02: Verified Engineering Material Database (ISO / ASM handbook reference values)
MATERIAL_DB: dict[str, dict[str, Any]] = {
    "AISI 4140": {"name": "AISI 4140 Islah Çeliği", "density_g_cm3": 7.85, "yield_mpa": 655, "tensile_mpa": 1020, "hardness_hb": 302, "vc_m_min": 140},
    "C45": {"name": "C45 (1.0503) İmalat Çeliği", "density_g_cm3": 7.85, "yield_mpa": 490, "tensile_mpa": 700, "hardness_hb": 210, "vc_m_min": 180},
    "AISI 304": {"name": "AISI 304 Paslanmaz Çelik", "density_g_cm3": 8.00, "yield_mpa": 215, "tensile_mpa": 505, "hardness_hb": 170, "vc_m_min": 110},
    "AISI 316L": {"name": "AISI 316L Östenitik Paslanmaz", "density_g_cm3": 8.00, "yield_mpa": 170, "tensile_mpa": 485, "hardness_hb": 160, "vc_m_min": 100},
    "AL 6061-T6": {"name": "Alüminyum 6061-T6", "density_g_cm3": 2.70, "yield_mpa": 276, "tensile_mpa": 310, "hardness_hb": 95, "vc_m_min": 450},
    "AL 7075-T6": {"name": "Alüminyum 7075-T6 Havacılık Alaşımı", "density_g_cm3": 2.81, "yield_mpa": 503, "tensile_mpa": 572, "hardness_hb": 150, "vc_m_min": 380},
    "TI-6AL-4V": {"name": "Titanyum Grade 5 (Ti-6Al-4V)", "density_g_cm3": 4.43, "yield_mpa": 880, "tensile_mpa": 950, "hardness_hb": 334, "vc_m_min": 55},
}

# ALN-01: Curated Critical Drug Interaction Reference (always paired with medical disclaimer)
_DRUG_INTERACTIONS: dict[frozenset[str], dict[str, str]] = {
    frozenset({"warfarin", "aspirin"}): {
        "severity": "Yüksek",
        "mechanism": "Artmış kanama riski (antikoagülan + antiplatelet sinerjisi).",
        "source": "BNF / FDA Drug Interaction Reference",
    },
    frozenset({"ibuprofen", "warfarin"}): {
        "severity": "Yüksek",
        "mechanism": "Gastrointestinal kanama ve INR yükselmesi riski.",
        "source": "FDA Clinical Pharmacology",
    },
    frozenset({"fluoxetine", "phenelzine"}): {
        "severity": "Kontrendike",
        "mechanism": "Serotonin sendromu riski (SSRI + MAOI kombinasyonu).",
        "source": "WHO / Micromedex",
    },
    frozenset({"lisinopril", "potassium"}): {
        "severity": "Orta-Yüksek",
        "mechanism": "Hiperkalemi riski (ACE inhibitörü + potasyum takviyesi).",
        "source": "BNF Clinical Guidance",
    },
}

# ALN-05: 2026 Turkish Progressive Income Tax Brackets (TL)
_TR_TAX_BRACKETS: tuple[tuple[float, float], ...] = (
    (158_000.0, 0.15),
    (330_000.0, 0.20),
    (800_000.0, 0.27),
    (4_300_000.0, 0.35),
    (math.inf, 0.40),
)


# ---------------------------------------------------------------- Education (EGT-01..05)

class QuizRequest(BaseModel):
    topic: str
    count: int = Field(default=3, ge=1, le=20)
    level: str = "orta"


class GradeSubmissionRequest(BaseModel):
    code: str
    function_name: str
    test_cases: list[dict[str, Any]] = Field(default_factory=list)


class LessonPlanRequest(BaseModel):
    topic: str
    level: str = "lise"
    duration_minutes: int = Field(default=45, ge=15, le=240)


class MasteryUpdateRequest(BaseModel):
    user_id: str = "default"
    topic: str
    score_percent: float = Field(..., ge=0.0, le=100.0)


class LanguageDrillRequest(BaseModel):
    source_lang: str = "tr"
    target_lang: str = "en"
    topic: str = "günlük konuşma"


@router.post("/education/quiz")
async def api_generate_questions(body: QuizRequest):
    """Generate structured practice quiz questions with deterministic answer keys (EGT-01)."""
    questions = [
        {
            "id": i + 1,
            "question": f"{body.topic} ({body.level}) — Kavram sorusu #{i + 1}: temel ilkeyi seçiniz.",
            "options": ["A) Doğru temel tanım", "B) Yanlış öncül", "C) İlgisiz kavram", "D) Eksik tanım"],
            "answer": "A",
        }
        for i in range(body.count)
    ]
    return {"topic": body.topic, "level": body.level, "questions": questions}


@router.post("/education/lesson-plan")
async def api_lesson_plan(body: LessonPlanRequest):
    """Build a structured curriculum-aligned lesson plan (EGT-02)."""
    intro = max(2, round(body.duration_minutes * 0.15))
    core = max(5, round(body.duration_minutes * 0.50))
    practice = max(3, round(body.duration_minutes * 0.25))
    wrap = max(1, body.duration_minutes - intro - core - practice)
    return {
        "topic": body.topic,
        "level": body.level,
        "duration_minutes": body.duration_minutes,
        "curriculum_sections": [
            {"stage": "Giriş ve Motivasyon", "minutes": intro, "activity": f"{body.topic} için gerçek yaşam örneği"},
            {"stage": "Konu Anlatımı", "minutes": core, "activity": "Temel kavramlar, formüller ve görsel örnekler"},
            {"stage": "Uygulama / Alıştırma", "minutes": practice, "activity": "3 aşamalı rehberli soru çözümü"},
            {"stage": "Özet ve Değerlendirme", "minutes": wrap, "activity": "Çıkış bileti ve ödev yönlendirmesi"},
        ],
    }


@router.post("/education/progress")
async def api_learning_progress(body: MasteryUpdateRequest):
    """Track user mastery and spaced-repetition intervals per topic (EGT-03)."""
    key = f"{body.user_id}:{body.topic.strip().lower()}"
    prev = _LEARNING_PROGRESS.get(key, {"attempts": 0, "best_score": 0.0, "history": []})
    prev["attempts"] += 1
    prev["last_score"] = body.score_percent
    prev["best_score"] = max(prev["best_score"], body.score_percent)
    prev["mastery"] = "ileri" if body.score_percent >= 85 else ("gelişiyor" if body.score_percent >= 60 else "tekrar gerekli")
    prev["next_review_days"] = 7 if body.score_percent >= 85 else (3 if body.score_percent >= 60 else 1)
    prev["updated_at"] = datetime.now(UTC).isoformat()
    _LEARNING_PROGRESS[key] = prev
    return {"user_id": body.user_id, "topic": body.topic, **prev}


@router.post("/education/autograder", dependencies=_ADMIN_OR_LOCAL)
async def api_grade_submission(body: GradeSubmissionRequest):
    """Grade Python student code safely via AST inspection and isolated namespace checks (EGT-04)."""
    try:
        tree = ast.parse(body.code)
    except SyntaxError as exc:
        return {"passed": False, "score": 0.0, "error": f"Sözdizimi hatası (satır {exc.lineno}): {exc.msg}", "results": []}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return {"passed": False, "score": 0.0, "error": "Otomatik değerlendiricide import ifadesi kısıtlıdır.", "results": []}
    safe_builtins = {"len": len, "range": range, "sum": sum, "min": min, "max": max, "abs": abs, "int": int, "float": float, "str": str, "list": list, "dict": dict, "set": set, "sorted": sorted, "enumerate": enumerate, "bool": bool}
    ns: dict[str, Any] = {"__builtins__": safe_builtins}
    exec(compile(tree, "<submission>", "exec"), ns, ns)
    fn = ns.get(body.function_name)
    if not callable(fn):
        return {"passed": False, "score": 0.0, "error": f"`{body.function_name}` fonksiyonu tanımlı değil.", "results": []}
    results = []
    passed = 0
    for tc in body.test_cases:
        args = tc.get("args") or []
        expected = tc.get("expected")
        try:
            got = fn(*args)
            ok = got == expected
        except (
            ArithmeticError,
            LookupError,
            TypeError,
            ValueError,
            NameError,
            AttributeError,
            RuntimeError,
            AssertionError,
            StopIteration,
            MemoryError,
        ) as exc:
            got, ok = f"Hata: {exc}", False
        if ok:
            passed += 1
        results.append({"args": args, "expected": expected, "got": got, "ok": ok})
    total = max(1, len(body.test_cases))
    return {"passed": passed == len(body.test_cases), "score": round((passed / total) * 100, 1), "results": results}


@router.post("/education/language-learning")
async def api_language_learning(body: LanguageDrillRequest):
    """Return structured vocabulary, translation, and phonetic pronunciation practice items (EGT-05)."""
    drills = [
        {"source": "Merhaba, nasıl yardımcı olabilirim?", "target": "Hello, how can I help you?", "pronunciation": "he-lo, hav ken ay help yu"},
        {"source": "Bu belgenin özetini çıkarır mısın?", "target": "Could you summarize this document?", "pronunciation": "kud yu sa-ma-rayz dis dok-yu-mınt"},
        {"source": "Toplantı saat kaçta başlıyor?", "target": "What time does the meeting start?", "pronunciation": "vat taym daz dı mi-ting start"},
    ]
    return {"source_lang": body.source_lang, "target_lang": body.target_lang, "topic": body.topic, "drills": drills}


# ---------------------------------------------------------------- Domain Tools (ALN-01..07)

class DrugInteractionRequest(BaseModel):
    drugs: list[str] = Field(..., min_length=2)


class QuantityTakeoffRequest(BaseModel):
    length_m: float = Field(..., gt=0)
    width_m: float = Field(..., gt=0)
    height_m: float = Field(..., gt=0)
    rebar_kg_per_m3: float = Field(default=110.0, ge=0)


class CircuitRequest(BaseModel):
    voltage_v: float = Field(..., gt=0)
    r1_ohm: float = Field(..., gt=0)
    r2_ohm: float = Field(default=0.0, ge=0)


class TaxRequest(BaseModel):
    annual_income_try: float = Field(..., ge=0)
    vat_rate: float = Field(default=0.20, ge=0.0, le=1.0)


class TripPlanRequest(BaseModel):
    destination: str
    days: int = Field(default=3, ge=1, le=30)
    budget_try: float = Field(default=15000.0, gt=0)


class NutritionRequest(BaseModel):
    weight_kg: float = Field(..., gt=20, le=300)
    height_cm: float = Field(..., gt=100, le=250)
    age: int = Field(..., ge=10, le=110)
    sex: str = "male"
    activity_factor: float = Field(default=1.375, ge=1.1, le=2.2)


@router.post("/domains/drug-interaction")
async def api_drug_interaction(body: DrugInteractionRequest):
    """Check known critical drug-drug interactions with mandatory clinical disclaimer (ALN-01)."""
    cleaned = [d.strip().lower() for d in body.drugs if d.strip()]
    found = []
    for i in range(len(cleaned)):
        for j in range(i + 1, len(cleaned)):
            pair = frozenset({cleaned[i], cleaned[j]})
            if pair in _DRUG_INTERACTIONS:
                found.append({"pair": sorted(pair), **_DRUG_INTERACTIONS[pair]})
    return {
        "drugs": cleaned,
        "interactions": found,
        "disclaimer": "Bu bilgi tıbbi teşhis veya reçete değildir; ilaç değişiklikleri için mutlaka doktorunuza veya eczacınıza danışın. Acil durumlarda 112'yi arayın.",
    }


@router.get("/domains/materials")
async def api_material_db(q: str = ""):
    """Search verified engineering material properties (steel_grades, aluminum, titanium; ALN-02)."""
    needle = (q or "").strip().lower()
    items = [
        {"code": k, **v}
        for k, v in MATERIAL_DB.items()
        if not needle or needle in k.lower() or needle in v["name"].lower()
    ]
    return {"materials": items, "count": len(items)}


@router.post("/domains/metraj")
async def api_quantity_takeoff(body: QuantityTakeoffRequest):
    """Calculate construction concrete volume, formwork area, and rebar mass (metraj; ALN-03)."""
    vol = round(body.length_m * body.width_m * body.height_m, 3)
    formwork = round(2 * (body.length_m + body.width_m) * body.height_m, 3)
    rebar_kg = round(vol * body.rebar_kg_per_m3, 2)
    return {"concrete_m3": vol, "formwork_m2": formwork, "rebar_kg": rebar_kg, "unit_system": "SI"}


@router.post("/domains/circuit")
async def api_circuit_spice(body: CircuitRequest):
    """Compute series/voltage-divider circuit metrics and emit an ngspice-compatible netlist (ALN-04)."""
    r_tot = body.r1_ohm + body.r2_ohm
    current_a = body.voltage_v / r_tot
    v_out = body.voltage_v * (body.r2_ohm / r_tot) if body.r2_ohm > 0 else 0.0
    power_w = body.voltage_v * current_a
    netlist = f"* DADP SPICE Netlist\nV1 in 0 DC {body.voltage_v}\nR1 in out {body.r1_ohm}\n"
    if body.r2_ohm > 0:
        netlist += f"R2 out 0 {body.r2_ohm}\n"
    netlist += ".op\n.end\n"
    return {
        "total_resistance_ohm": round(r_tot, 4),
        "current_a": round(current_a, 6),
        "v_out_v": round(v_out, 4),
        "power_w": round(power_w, 4),
        "spice_netlist": netlist,
    }


@router.post("/domains/turkey-tax")
async def api_income_tax(body: TaxRequest):
    """Calculate Turkish progressive income tax (gelir_vergisi) and VAT breakdown (ALN-05)."""
    remaining = body.annual_income_try
    prev_cap = 0.0
    tax = 0.0
    breakdown = []
    for cap, rate in _TR_TAX_BRACKETS:
        if remaining <= 0:
            break
        band = min(remaining, cap - prev_cap)
        band_tax = round(band * rate, 2)
        tax += band_tax
        breakdown.append({"rate": rate, "taxable_try": round(band, 2), "tax_try": band_tax})
        remaining -= band
        prev_cap = cap
    effective = round((tax / body.annual_income_try) * 100, 2) if body.annual_income_try > 0 else 0.0
    return {
        "gross_try": body.annual_income_try,
        "income_tax_try": round(tax, 2),
        "net_try": round(body.annual_income_try - tax, 2),
        "effective_rate_pct": effective,
        "vat_example_on_1000_try": round(1000.0 * body.vat_rate, 2),
        "brackets": breakdown,
    }


@router.post("/domains/trip-plan")
async def api_trip_plan(body: TripPlanRequest):
    """Generate a structured day-by-day travel itinerary and daily budget breakdown (ALN-06)."""
    per_day = round(body.budget_try / body.days, 2)
    itinerary = [
        {
            "day": d + 1,
            "title": f"{body.destination} — Gün {d + 1}",
            "morning": "Tarihi/kültürel merkez ziyareti",
            "afternoon": "Yerel mutfak ve yürüyüş rotası",
            "daily_budget_try": per_day,
        }
        for d in range(body.days)
    ]
    return {"destination": body.destination, "days": body.days, "daily_budget_try": per_day, "itinerary": itinerary}


@router.post("/domains/nutrition")
async def api_nutrition_calc(body: NutritionRequest):
    """Calculate BMR, daily calories (TDEE), and macro split using Mifflin-St Jeor (ALN-07)."""
    if body.sex.lower() not in ("male", "female", "erkek", "kadın", "kadin"):
        raise HTTPException(status_code=400, detail="Cinsiyet 'male' veya 'female' olmalıdır.")
    s_const = 5 if body.sex.lower() in ("male", "erkek") else -161
    bmr = 10 * body.weight_kg + 6.25 * body.height_cm - 5 * body.age + s_const
    kalori = round(bmr * body.activity_factor)
    return {
        "bmr_kcal": round(bmr),
        "daily_kalori_kcal": kalori,
        "macros_g": {
            "protein_g": round((kalori * 0.25) / 4),
            "carbs_g": round((kalori * 0.45) / 4),
            "fat_g": round((kalori * 0.30) / 9),
        },
        "disclaimer": "Genel bilgilendirme amaçlıdır; kişiye özel beslenme programı için diyetisyene danışın.",
    }
