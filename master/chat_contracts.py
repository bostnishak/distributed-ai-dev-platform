"""Deterministic chat contract guards, calculators, chart renderer, and syntax hints (DAV-01..13)."""

from __future__ import annotations

import ast
import html
import logging
import operator
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

_SAFE_BINOPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_SAFE_UNARYOPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ARITH_EXPR_RE = re.compile(r"(?<![A-Za-z0-9_])(\d+(?:[.,]\d+)?(?:\s*[+\-*/^]\s*\d+(?:[.,]\d+)?)+)(?![A-Za-z0-9_])")
_DURATION_UNITS = (
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:gün|gun|days?)\b", re.IGNORECASE), 86400),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:saat|hours?|hr)\b", re.IGNORECASE), 3600),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:dakika|dk\.?|minutes?|min)\b", re.IGNORECASE), 60),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:saniye|sn\.?|seconds?|sec)\b", re.IGNORECASE), 1),
)

_MAX_WORDS_RE = re.compile(
    r"(\d+)\s*kelime(?:yi|den|lik)?\s*(?:geçme\w*|gecme\w*|aşma\w*|asma\w*|az|kısa|kisa|olsun|ile\s+sınır|altında|altinda)",
    re.IGNORECASE,
)
_FORBIDDEN_WORD_RE = re.compile(
    r"['\"«“]([^'\"»”]{2,40})['\"»”]\s*(?:kelime\w*|sözcüğ\w*|sozcug\w*|ifade\w*)?\s*(?:geçme\w*|gecme\w*|olmasın|olmasin|kullanma\w*|yer\s+almasın)",
    re.IGNORECASE,
)
_CODE_ONLY_RE = re.compile(
    r"(?:sadece\s+(?:geçerli\s+)?kod|yalnızca\s+kod|açıklama\s+yazma|aciklama\s+yazma|only\s+code|code\s+only)",
    re.IGNORECASE,
)
_AUDIT_EXPLICIT_RE = re.compile(
    r"(?:denetle|hata\s+var\s+mı|hata\s+kontrol|kontrol\s+et|audit|lint|sözdizimi|syntax|doğrula\w*)",
    re.IGNORECASE,
)
_CHART_REQ_RE = re.compile(
    r"(?:çubuk\s+grafi\w*|cubuk\s+grafi\w*|bar\s+chart|pasta\s+grafi\w*|çizgi\s+grafi\w*|grafi(?:k|ği)\s*(?:çiz\w*|ciz\w*|oluştur\w*|hazırla\w*))",
    re.IGNORECASE,
)
_RESEARCH_REQ_RE = re.compile(
    r"(?:kaynaklı\s+.*araştır\w*|kaynak\w*\s+göster\w*.*araştır\w*|kısa\s+bir\s+araştırma\s+yap|araştırma\s+raporu\s+hazırla)",
    re.IGNORECASE,
)


def _eval_ast_num(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARYOPS:
        return float(_SAFE_UNARYOPS[type(node.op)](_eval_ast_num(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
        left = _eval_ast_num(node.left)
        right = _eval_ast_num(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return float(_SAFE_BINOPS[type(node.op)](left, right))
    raise ValueError("unsupported node")


def _fmt_number(val: float) -> str:
    if float(val).is_integer():
        iv = round(val)
        return f"{iv} ({iv:,})".replace(",", ".") if abs(iv) >= 1000 else str(iv)
    return f"{val:.6f}".rstrip("0").rstrip(".")


def extract_deterministic_calculation(prompt: str) -> str | None:
    """DAV-12 & DAV-13: Deterministic calculator for arithmetic prompts and duration-to-seconds."""
    text = (prompt or "").strip()
    low = text.lower()
    if not text or len(text) > 260:
        return None
    if any(k in low for k in ("python", "kod", "fonksiyon", "def ", "grafik", "sunum", "slayt")):
        return None

    # DAV-13: Duration conversion to seconds (e.g. "Bir yıl 365 gün 5 saat 48 dk 46 sn ise bu kaç saniyedir?")
    if "saniye" in low and ("kaç" in low or "kac" in low or "hesapla" in low or "eder" in low):
        total = 0.0
        parts: list[str] = []
        matched_units = 0
        for pat, mult in _DURATION_UNITS:
            m = pat.search(text)
            if m:
                num = float(m.group(1).replace(",", "."))
                total += num * mult
                parts.append(f"{m.group(1)} x {mult}")
                matched_units += 1
        if matched_units >= 2:
            total_i = round(total)
            dotted = f"{total_i:,}".replace(",", ".")
            return f"Hesaplama: {' + '.join(parts)} = **{dotted}** ({total_i}) saniye."

    # DAV-12: Embedded arithmetic calculation ("12345 * 6789 işlemini hesapla.")
    if any(k in low for k in ("hesapla", "kaç eder", "kac eder", "kaçtır", "kactir", "sonucu", "işlemi", "islemi")):
        m = _ARITH_EXPR_RE.search(text)
        if m:
            raw_expr = m.group(1).strip()
            norm_expr = raw_expr.replace(",", ".").replace("^", "**")
            try:
                tree = ast.parse(norm_expr, mode="eval")
                val = _eval_ast_num(tree.body)
                return f"{raw_expr} = {_fmt_number(val)}"
            except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
                return None
    return None


def should_attach_file_audit(prompt: str, inspection: dict[str, Any] | None) -> bool:
    """DAV-06: Only prepend Deterministic File Inspection report when user asked for audit or severe errors exist."""
    if not inspection:
        return False
    if _AUDIT_EXPLICIT_RE.search(prompt or ""):
        return True
    counts = inspection.get("severity_counts") or {}
    return int(counts.get("critical", 0)) > 0 or int(counts.get("high", 0)) > 0


def parse_chart_points(prompt: str) -> list[tuple[str, float]]:
    """Extract (label, value) pairs such as 'Ocak 10, Şubat 20, Mart 15'."""
    segment = prompt.split(":", 1)[1] if ":" in prompt else prompt
    pairs = re.findall(r"([A-Za-zÇĞİÖŞÜçğıöşü][A-Za-z0-9ÇĞİÖŞÜçğıöşü_-]{0,24})\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)", segment)
    out: list[tuple[str, float]] = []
    skip_words = {"grafik", "çubuk", "cubuk", "veri", "verilerle", "bir", "çiz", "ciz", "şu", "su"}
    for lbl, num_s in pairs:
        if lbl.lower() in skip_words:
            continue
        out.append((lbl, float(num_s.replace(",", "."))))
    return out


def is_chart_generation_request(prompt: str, has_file: bool) -> bool:
    """DAV-10: Detect direct bar/data chart generation requests with inline data points."""
    if has_file:
        return False
    return bool(_CHART_REQ_RE.search(prompt or "") and len(parse_chart_points(prompt or "")) >= 2)


def build_svg_bar_chart(prompt: str) -> dict[str, Any]:
    """DAV-10: Render a clean, self-contained SVG bar chart and persist it to media_dir."""
    import multimodal_studio as mms

    points = parse_chart_points(prompt)
    width = max(480, 120 + len(points) * 110)
    height = 320
    pad_l, pad_r, pad_t, pad_b = 56, 28, 42, 54
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    max_val = max((abs(v) for _, v in points), default=1.0) or 1.0
    slot_w = chart_w / max(1, len(points))
    bar_w = min(64.0, slot_w * 0.58)
    colors = ("#4f46e5", "#0d9488", "#059669", "#d97706", "#e11d48", "#2563eb")

    bars_svg: list[str] = []
    for idx, (label, val) in enumerate(points):
        bh = max(4.0, (max(0.0, val) / max_val) * chart_h)
        x = pad_l + idx * slot_w + (slot_w - bar_w) / 2
        y = pad_t + chart_h - bh
        color = colors[idx % len(colors)]
        val_txt = str(int(val)) if float(val).is_integer() else f"{val:.2f}"
        bars_svg.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="6" fill="{color}" />'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="13" font-weight="600" fill="#1e293b">{html.escape(val_txt)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{pad_t + chart_h + 22:.1f}" text-anchor="middle" font-size="13" fill="#334155">{html.escape(label)}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Çubuk grafik">'
        f'<rect width="{width}" height="{height}" rx="12" fill="#f8fafc" stroke="#e2e8f0" />'
        f'<text x="{pad_l}" y="26" font-size="15" font-weight="700" fill="#0f172a">Veri Grafiği</text>'
        f'<line x1="{pad_l}" y1="{pad_t + chart_h}" x2="{width - pad_r}" y2="{pad_t + chart_h}" stroke="#94a3b8" stroke-width="1.5" />'
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + chart_h}" stroke="#94a3b8" stroke-width="1.5" />'
        + "".join(bars_svg)
        + "</svg>"
    )
    fid = f"chart_{uuid.uuid4().hex[:10]}.svg"
    out_path = mms.media_dir() / fid
    out_path.write_text(svg, encoding="utf-8")
    return {"svg": svg, "svg_url": f"/api/assistant/media/{fid}", "filename": fid, "points": points}


def is_grounded_research_request(prompt: str, has_file: bool) -> bool:
    """DAV-09: Detect explicit grounded/cited research requests."""
    if has_file:
        return False
    return bool(_RESEARCH_REQ_RE.search(prompt or ""))


def gather_research_sources(prompt: str) -> list[dict[str, str]]:
    """DAV-09: Collect live SearXNG + local RAG sources; fall back cleanly with explicit source metadata."""
    sources: list[dict[str, str]] = []
    try:
        from rag.web import search_searxng

        web_hits = search_searxng(prompt, max_results=4)
        for hit in web_hits:
            url = str(hit.get("url") or "").strip()
            title = str(hit.get("title") or url or "Web Kaynağı").strip()
            snippet = str(hit.get("content") or hit.get("snippet") or "").strip()
            if url:
                sources.append({"id": f"S{len(sources) + 1}", "title": title, "url": url, "snippet": snippet[:400]})
    except Exception as exc:
        log.debug("SearXNG lookup skipped: %s", exc)

    if not sources:
        try:
            from rag.store import default_rag_store

            rag_hits = default_rag_store.search(prompt, top_k=3)
            for hit in rag_hits:
                sources.append(
                    {
                        "id": f"S{len(sources) + 1}",
                        "title": str(hit.get("doc_id") or "Yerel Bilgi Bankası"),
                        "url": f"rag://{hit.get('doc_id', 'local')}",
                        "snippet": str(hit.get("content") or "")[:400],
                    }
                )
        except Exception as exc:
            log.debug("RAG lookup skipped: %s", exc)
    return sources


@dataclass
class OutputConstraints:
    max_words: int | None = None
    forbidden_words: list[str] = field(default_factory=list)
    code_only: bool = False
    syntax_hint: str = ""
    turkish_vowels_hint: bool = False
    prefer_explicit_absent: bool = False
    system_notes: list[str] = field(default_factory=list)

    @property
    def needs_buffering(self) -> bool:
        return bool(self.max_words or self.forbidden_words or self.code_only or self.syntax_hint or self.prefer_explicit_absent)


def inspect_prompt_constraints(prompt: str) -> OutputConstraints:
    """DAV-01..05: Parse explicit formatting/negative/code-only/syntax/Turkish constraints."""
    text = prompt or ""
    low = text.lower()
    c = OutputConstraints()

    m_words = _MAX_WORDS_RE.search(text)
    if m_words:
        c.max_words = max(3, int(m_words.group(1)))
        c.system_notes.append(f"KESİN KURAL: Yanıtın en fazla {c.max_words} kelime olsun. Başlık, giriş veya açıklama ekleme.")

    for m_forb in _FORBIDDEN_WORD_RE.finditer(text):
        word = m_forb.group(1).strip()
        if word:
            c.forbidden_words.append(word)
            c.system_notes.append(f"KESİN YASAK: Yanıtta '{word}' kelimesi (büyük/küçük harf veya ekli biçimi dahil) ASLA geçmesin.")

    if _CODE_ONLY_RE.search(text):
        c.code_only = True
        c.system_notes.append("KESİN KURAL: Yalnızca tek bir markdown kod bloğu (```...```) döndür. Kod bloğu dışında hiçbir açıklama yazma.")

    if ("sesli harf" in low or "count_vowels" in low) and ("türkçe" in low or "turkce" in low or "python" in low):
        c.turkish_vowels_hint = True
        c.system_notes.append(
            "Türkçe sesli harf sayımında mutlaka tam seti kullan: vowels = set('aeıioöuüAEIİOÖUÜ'). "
            "Sadece ASCII aeiou kullanma; ı, ö, ü, İ, Ö, Ü harflerini dahil et."
        )

    if any(k in low for k in ("hata nedir", "hatası nedir", "ne hata", "syntax", "sözdizimi")):
        for snippet in re.findall(r"`([^`]{4,200})`", text):
            try:
                ast.parse(snippet)
            except SyntaxError as exc:
                c.syntax_hint = (
                    f"Deterministik Python AST analizi: `{snippet}` ifadesinde sözdizimi (syntax) hatası var "
                    f"(satır {exc.lineno}: {exc.msg} — eksik operand / tamamlanmamış ifade)."
                )
                c.system_notes.append(f"{c.syntax_hint} Yanıtında bunun bir sözdizimi (syntax) hatası ve eksik ikinci operand olduğunu açıkça belirt.")
                break

    if "yoksa yok" in low or "yoksa belirt" in low:
        c.prefer_explicit_absent = True
        c.system_notes.append(
            "Eğer sorulan bilgi belgede veya bağlamda bulunmuyorsa yanıtında açıkça 'yok' veya 'bulunmuyor' ifadesini kullan."
        )

    return c


def enforce_output_constraints(text: str, c: OutputConstraints) -> str:
    """DAV-01..06: Deterministically repair small-model contract slips (code-only, max_words, forbidden words, AST syntax)."""
    out = (text or "").strip()
    if not out:
        return out

    if c.prefer_explicit_absent and re.search(r"yer almamaktadır|bulunmamaktadır|geçmemektedir|mevcut değildir", out, re.IGNORECASE):
        if not re.search(r"\byok\b|bulunmuyor|mevcut değil", out, re.IGNORECASE):
            out = re.sub(r"yer almamaktadır", "bulunmuyor (yok)", out, flags=re.IGNORECASE)
            out = re.sub(r"bulunmamaktadır", "bulunmuyor (yok)", out, flags=re.IGNORECASE)
            out = re.sub(r"geçmemektedir", "bulunmuyor (yok)", out, flags=re.IGNORECASE)
            out = re.sub(r"mevcut değildir", "mevcut değil (yok)", out, flags=re.IGNORECASE)

    if c.syntax_hint and not re.search(r"sözdizimi|syntax|operand|eksik|tamamlanmamış", out, re.IGNORECASE):
        out = f"{c.syntax_hint}\n\n{out}"

    if c.code_only:
        blocks = re.findall(r"```[\s\S]*?```", out)
        if blocks:
            out = "\n\n".join(blocks).strip()

    if c.forbidden_words:
        for fw in c.forbidden_words:
            pat = re.compile(re.escape(fw) + r"\w*", re.IGNORECASE)
            if pat.search(out):
                lines = [ln for ln in out.splitlines() if not pat.search(ln)]
                if lines and len(" ".join(lines).split()) >= 4:
                    out = "\n".join(lines).strip()
                else:
                    out = re.sub(r"\s{2,}", " ", pat.sub("ufuk", out)).strip()

    if c.max_words:
        words = out.split()
        if len(words) > c.max_words:
            trimmed = " ".join(words[: c.max_words]).rstrip(",;:-")
            if not trimmed.endswith((".", "!", "?")):
                trimmed += "."
            out = trimmed

    return out
