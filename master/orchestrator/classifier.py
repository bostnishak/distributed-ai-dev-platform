"""ORC-02, ORC-03, ORC-04, ORC-20: Fast Zero-LLM Intent Classifier, Multi-Intent Decomposer & Language Detector."""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

INTENTS_YAML_PATH = Path(__file__).resolve().parent / "intents.yaml"

_TR_CHARS_RE = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
_TR_STOPWORDS = frozenset({
    "ve", "ile", "bir", "bu", "şu", "için", "nasıl", "nedir", "bana", "benim",
    "yap", "yaz", "oluştur", "hazırla", "anlat", "çevir", "özetle", "sadece",
    "kısa", "ders", "kod", "sunum", "proje", "dosya", "hesapla", "merhaba", "selam",
})
_EN_STOPWORDS = frozenset({
    "the", "and", "for", "with", "this", "that", "how", "what", "write",
    "create", "build", "make", "explain", "teach", "only", "code", "short",
    "briefly", "summarize", "translate", "calculate", "hello", "please",
})

_EXPLICIT_EN_RE = re.compile(r"\b(ingilizce|in english|answer in english|english only)\b", re.IGNORECASE)
_EXPLICIT_TR_RE = re.compile(r"\b(türkçe|turkce|in turkish|türkçe cevapla|türkçe anlat)\b", re.IGNORECASE)

_MULTI_SPLIT_RE = re.compile(
    r"(?:\b(?:sonra|ardından|daha sonra|ve ayrıca|ayrıca|bir de|then|and then|after that)\b|[;])",
    re.IGNORECASE,
)

# High-precision keyword signals per intent to sharpen disambiguation under 5 ms
_LEXICAL_SIGNALS: dict[str, tuple[str, ...]] = {
    "greeting": ("merhaba", "selam", "günaydın", "iyi akşamlar", "nasılsın", "hello", "hey"),
    "code_only": ("sadece kod", "yalnızca kod", "açıklamasız kod", "code only", "only code"),
    "code_fix": ("hatayı düzelt", "debug", "traceback", "refactor", "fix this", "bugları"),
    "code_write": ("fonksiyonu yaz", "kodu yaz", "kodla", "write a python", "endpointi oluştur", "script"),
    "lesson": ("öğret", "ders anlat", "sıfırdan anlat", "teach me", "ders gibi"),
    "project_build": ("tam proje", "web sitesi", "fullstack", "uygulama kur", "projesi oluştur", "projesi yap"),
    "game_build": ("oyunu yap", "yılan oyunu", "tetris", "canvas", "oyun geliştir", "playable"),
    "presentation": ("powerpoint", "pptx", "slayt", "sunum hazırla", "sunumu hazırla", "presentation"),
    "document_gen": ("docx", "word raporu", "pdf rapor", "xlsx", "excel", "şartname"),
    "research": ("araştır", "kaynaklı", "literatür", "kaynaklarıyla", "deep research", "citations"),
    "data_analysis": ("csv", "veri seti", "korelasyon", "trend analizi", "dataset", "sql sorgusu"),
    "image_gen": ("görseli çiz", "resmi oluştur", "infografik", "logo", "svg", "illustration", "diyagram"),
    "image_explain": ("fotoğrafta", "ekran görüntüsü", "resimdeki", "uploaded image", "görseli yorumla"),
    "audio_transcribe": ("ses kaydını", "transkripsiyon", "mp3", "transcribe", "yazıya dök", "sesli mesaj"),
    "translate": ("çevir", "tercüme", "translate", "çeviri yap", "ingilizceye", "türkçeye"),
    "summarize": ("özetle", "özetini", "summarize", "ana maddelerini", "özet geç"),
    "math_calc": ("hesapla", "denklemini çöz", "bileşik faiz", "türev", "integral", "calculate", "derivative"),
    "legal_info": ("sözleşme", "kvkk", "kanunu", "hukuki", "mevzuat", "nda", "legal risk", "kıdem tazminatı"),
    "finance_dcf": ("dcf", "wacc", "nakit akışı", "değerleme", "irr", "npv", "discounted cash flow"),
    "health_info": ("tansiyon", "belirtileri", "tıbbi", "migren", "vitamini", "kan şekeri", "medical"),
    "cnc_engineering": ("cnc", "gd&t", "tolerans", "balonlama", "iso 2768", "freze", "tornalama", "pürüzlülük"),
    "file_convert": ("formatına çevir", "formatına dönüştür", "convert this pdf", "docx formatına", "dönüştür"),
    "archive_zip": ("ziple", "zip dosyası", "zip arşiv", "sıkıştır", "extract this zip", "arşivde paketle"),
    "automation_mcp": ("mcp", "connector", "webhook", "otomasyon", "entegrasyonu"),
    "prompt_distill": ("sohbeti prompt", "sistem promptu", "prompt şablonu", "reusable system prompt"),
    "cross_chat": ("diğer sohbetlerimde", "geçmiş sohbet", "sohbetler arası", "previous chats", "önceki konuşmalarımda"),
    "short_answer": ("kısaca", "tek cümlede", "kısa tut", "briefly", "one sentence", "uzatmadan", "en fazla iki cümle"),
    "targeted_edit": ("sadece 3. slayt", "yalnızca", "diğerlerine dokunma", "edit only", "untouched", "revize et"),
}


@dataclass(frozen=True)
class IntentSpec:
    id: str
    route: str
    mode: str
    tier: str
    risk: str
    verify_profile: str
    tools: tuple[str, ...]
    required_inputs: tuple[str, ...]
    examples: tuple[str, ...]


@dataclass
class IntentDecision:
    intent: str
    confidence: float
    route: str
    mode: str
    tier: str
    risk: str
    verify_profile: str
    tools: list[str]
    required_inputs: list[str]
    language: str
    sub_intents: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    catalog_version: str = "2.0.0"


def _normalize(text: str) -> str:
    tr = (text or "").replace("İ", "i").replace("I", "ı").strip().lower()
    return re.sub(r"\s+", " ", tr)


def detect_language(text: str) -> str:
    """ORC-20: Detect user language ('tr' or 'en') with explicit override support."""
    norm = _normalize(text)
    if _EXPLICIT_EN_RE.search(norm):
        return "en"
    if _EXPLICIT_TR_RE.search(norm):
        return "tr"
    if _TR_CHARS_RE.search(text or ""):
        return "tr"
    words = set(re.findall(r"[a-zA-Zçğıöşü]+", norm))
    tr_hits = len(words & _TR_STOPWORDS)
    en_hits = len(words & _EN_STOPWORDS)
    if en_hits > tr_hits and en_hits >= 1:
        return "en"
    return "tr"


def _tokenize(text: str) -> list[str]:
    norm = _normalize(text)
    words = re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ_&]+", norm)
    tokens = list(words)
    # Add word bigrams for phrase sensitivity
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i + 1]}")
    # Add 4-char n-grams for Turkish agglutinative morphology
    for w in words:
        if len(w) >= 5:
            for j in range(len(w) - 3):
                tokens.append(f"#{w[j:j + 4]}")
    return tokens


@lru_cache(maxsize=1)
def load_intent_catalog() -> tuple[str, dict[str, IntentSpec]]:
    raw = yaml.safe_load(INTENTS_YAML_PATH.read_text(encoding="utf-8"))
    version = str(raw.get("version") or "2.0.0")
    specs: dict[str, IntentSpec] = {}
    for item in raw.get("intents") or []:
        spec = IntentSpec(
            id=str(item["id"]),
            route=str(item["route"]),
            mode=str(item["mode"]),
            tier=str(item.get("tier") or "standard"),
            risk=str(item.get("risk") or "low"),
            verify_profile=str(item.get("verify_profile") or "basic"),
            tools=tuple(item.get("tools") or ()),
            required_inputs=tuple(item.get("required_inputs") or ()),
            examples=tuple(item.get("examples") or ()),
        )
        specs[spec.id] = spec
    return version, specs


@lru_cache(maxsize=1)
def _build_tfidf_index() -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    _, specs = load_intent_catalog()
    doc_freqs: Counter[str] = Counter()
    intent_tfs: dict[str, Counter[str]] = {}
    for intent_id, spec in specs.items():
        c: Counter[str] = Counter()
        for ex in spec.examples:
            c.update(_tokenize(ex))
        for sig in _LEXICAL_SIGNALS.get(intent_id, ()):
            c.update(_tokenize(sig))
        intent_tfs[intent_id] = c
        for tok in c:
            doc_freqs[tok] += 1

    n_docs = max(1, len(specs))
    idf = {tok: math.log((n_docs + 1) / (df + 1)) + 1.0 for tok, df in doc_freqs.items()}
    vectors: dict[str, dict[str, float]] = {}
    for intent_id, tf in intent_tfs.items():
        vec = {tok: cnt * idf.get(tok, 1.0) for tok, cnt in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors[intent_id] = {tok: v / norm for tok, v in vec.items()}
    return vectors, idf


def _score_single_utterance(text: str) -> tuple[str, float]:
    norm = _normalize(text)
    if not norm:
        return "chat", 0.5

    vectors, idf = _build_tfidf_index()
    q_tf = Counter(_tokenize(norm))
    q_vec = {tok: cnt * idf.get(tok, 1.0) for tok, cnt in q_tf.items()}
    q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
    q_unit = {tok: v / q_norm for tok, v in q_vec.items()}

    best_id = "chat"
    best_score = 0.0

    for intent_id, vec in vectors.items():
        sim = sum(val * vec.get(tok, 0.0) for tok, val in q_unit.items())
        # Lexical precision bonus
        bonus = 0.0
        for sig in _LEXICAL_SIGNALS.get(intent_id, ()):
            if sig in norm:
                bonus += 0.32 if " " in sig else 0.22
        # Greeting should only dominate on short standalone greetings
        if intent_id == "greeting" and len(norm.split()) > 6:
            sim *= 0.25
            bonus *= 0.2
        score = sim + min(bonus, 0.65)
        if score > best_score:
            best_score = score
            best_id = intent_id

    confidence = round(min(0.99, max(0.25, best_score)), 3)
    return best_id, confidence


def decompose_multi_intent(text: str) -> list[dict[str, Any]]:
    """ORC-04: Split compound requests into ordered sub-intent steps."""
    raw = (text or "").strip()
    if not raw:
        return []
    parts = [p.strip(" ,.") for p in _MULTI_SPLIT_RE.split(raw) if len(p.strip(" ,.")) >= 4]
    if len(parts) <= 1:
        return []
    _, specs = load_intent_catalog()
    sub: list[dict[str, Any]] = []
    for idx, part in enumerate(parts, start=1):
        intent_id, conf = _score_single_utterance(part)
        spec = specs[intent_id]
        sub.append({
            "step": idx,
            "text": part,
            "intent": intent_id,
            "confidence": conf,
            "mode": spec.mode,
            "route": spec.route,
            "tools": list(spec.tools),
        })
    distinct = {s["intent"] for s in sub}
    return sub if len(distinct) >= 2 or len(sub) >= 2 else []


def classify_intent(text: str, *, mode_override: str | None = None) -> IntentDecision:
    """ORC-02: Classify prompt into one of 30 intents in < 10 ms without calling an LLM."""
    t0 = time.perf_counter()
    version, specs = load_intent_catalog()
    lang = detect_language(text)
    sub_intents = decompose_multi_intent(text)
    intent_id, conf = _score_single_utterance(text)
    spec = specs[intent_id]
    final_mode = mode_override or spec.mode
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return IntentDecision(
        intent=spec.id,
        confidence=conf,
        route=spec.route,
        mode=final_mode,
        tier=spec.tier,
        risk=spec.risk,
        verify_profile=spec.verify_profile,
        tools=list(spec.tools),
        required_inputs=list(spec.required_inputs),
        language=lang,
        sub_intents=sub_intents,
        latency_ms=latency_ms,
        catalog_version=version,
    )
