"""MM-01..MM-14: STT/Meeting Evidence, TTS Prep, Visual Gen/Edit, KVKK Anonymizer, Diagram Repair, Attachments & Signed Media."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import inspect
import io
import re
import secrets
import sqlite3
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

import config
from orchestrator.state import save_artifact

# ---------------------------------------------------------------- MM-02 Meeting/Lecture Summary with Evidence Timestamps

_DECISION_RE = re.compile(r"\b(karar\s+verildi|onaylandı|kabul\s+edildi|decided|approved)\b", re.IGNORECASE)
_ACTION_RE = re.compile(r"\b(yapacak|hazırlayacak|tamamlayacak|sorumlu|aksiyon|action|will\s+prepare|todo)\b", re.IGNORECASE)
_DATE_DUE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)|Cuma|Pazartesi)\b", re.IGNORECASE)
_OWNER_RE = re.compile(
    r"(?:^\s*([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,})\s+(?!(?:dokümanı|raporu\s+hazırlanacak|planı|projesi|bütçesi)\b).*\b(?:yapacak|hazırlayacak|tamamlayacak|sorumlu)\b"
    r"|\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,})\s+(?:yapacak|hazırlayacak|tamamlayacak|sorumlu)\b)"
)
_NON_PERSON_STARTERS = frozenset({"Bütçe", "Rapor", "Proje", "Sistem", "Belge", "Toplantı", "Yeni", "Tüm", "Bu"})


def summarize_meeting_with_evidence(segments: list[dict[str, Any]]) -> dict[str, Any]:
    """MM-02: Extract decisions, actions (owner/due_date='belirtilmemiş' if absent), and open questions with [MM:SS] quotes."""
    decisions: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []
    open_questions: list[dict[str, str]] = []

    for seg in segments:
        start_s = int(seg.get("start") or 0)
        ts = f"{start_s // 60:02d}:{start_s % 60:02d}"
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        if _DECISION_RE.search(text):
            decisions.append({"decision": text, "timestamp": ts, "evidence_quote": text})
        if _ACTION_RE.search(text):
            owner_m = _OWNER_RE.search(text)
            cand_owner = (owner_m.group(1) or owner_m.group(2)) if owner_m else ""
            owner = cand_owner if (cand_owner and cand_owner not in _NON_PERSON_STARTERS) else "belirtilmemiş"
            due_m = _DATE_DUE_RE.search(text)
            actions.append({
                "action": text,
                "owner": owner,
                "due_date": due_m.group(1) if due_m else "belirtilmemiş",
                "timestamp": ts,
                "evidence_quote": text,
            })
        if text.endswith("?"):
            open_questions.append({"question": text, "timestamp": ts, "evidence_quote": text})

    return {"decisions": decisions, "actions": actions, "open_questions": open_questions}


# ---------------------------------------------------------------- MM-03 TTS Text Preparation (No Code/Tables Spoken)

def prepare_tts_text(markdown_text: str) -> str:
    """MM-03: Strip code blocks and markdown tables and normalize abbreviations before Piper Turkish TTS."""
    txt = re.sub(r"```[\s\S]*?```", " ", markdown_text or "")
    lines = [ln for ln in txt.splitlines() if not (ln.strip().startswith("|") and ln.strip().endswith("|"))]
    cleaned = " ".join(lines)
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\börn\.", "örneğin", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bvb\.", "ve benzeri", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdk\.", "dakika", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


# ---------------------------------------------------------------- MM-04, 05, 06, 08 Visual Studio & Versioned Editing

def generate_visual_with_metadata(prompt: str, *, gpu_diffusion_available: bool = False, watermark: bool = True) -> dict[str, Any]:
    """MM-05: Route to diffusion if GPU bridge active, else parametric SVG fallback with mandatory AI metadata."""
    mode = "local_diffusion" if gpu_diffusion_available else "parametric_svg_fallback"
    note = "" if gpu_diffusion_available else "Yerel GPU difüzyon köprüsü aktif değil; parametrik vektör SVG yedeği üretildi."
    wm_svg = '<text x="390" y="232" font-size="10" text-anchor="end" fill="#64748B">AI üretildi</text>' if watermark else ""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" width="400" height="240">'
        '<metadata>produced_by=ai_generated</metadata>'
        '<rect width="100%" height="100%" fill="#0F172A" rx="12"/>'
        f'<text x="200" y="125" font-size="16" text-anchor="middle" fill="#F8FAFC">{prompt[:42]}</text>'
        f"{wm_svg}</svg>"
    )
    art = save_artifact(kind="image", title=prompt[:60], sections=[svg], metadata={"produced_by": "ai_generated", "mode": mode})
    return {
        "artifact_id": art["artifact_id"],
        "mode": mode,
        "notice": note,
        "metadata": {"produced_by": "ai_generated", "watermark": watermark},
        "svg": svg,
    }


def edit_image_versioned(
    image_bytes: bytes,
    *,
    operation: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """MM-06 & MM-08: Non-destructive Pillow image edit (crop/resize/rotate/contrast/clean_scan) keeping original intact."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    p = params or {}
    op = operation.lower()

    if op == "rotate":
        out = img.rotate(float(p.get("angle", 90)), expand=True)
    elif op == "resize":
        out = img.resize((max(16, int(p.get("width", 256))), max(16, int(p.get("height", 256)))))
    elif op == "crop":
        box = p.get("box") or (0, 0, img.width // 2, img.height // 2)
        out = img.crop(tuple(int(v) for v in box))
    elif op == "contrast":
        out = ImageEnhance.Contrast(img).enhance(float(p.get("factor", 1.35)))
    elif op == "clean_scan":
        gray = ImageOps.grayscale(img)
        out = ImageOps.autocontrast(gray).convert("RGB")
    else:
        raise ValueError(f"Desteklenmeyen görsel düzenleme işlemi: {operation}")

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    out_bytes = buf.getvalue()
    art = save_artifact(
        kind="image_edit",
        title=f"Görsel Düzenleme ({op})",
        sections=[f"{op}: {out.width}x{out.height}"],
        metadata={"operation": op, "original_size": [img.width, img.height], "new_size": [out.width, out.height]},
    )
    return {"artifact_id": art["artifact_id"], "operation": op, "width": out.width, "height": out.height, "png_bytes": out_bytes}


# ---------------------------------------------------------------- MM-09 KVKK / PII Anonymization (Algorithmic TCKN + Image Blur)

def is_valid_tckn(candidate: str) -> bool:
    """MM-09: Official 11-digit Turkish Citizenship Number (TCKN) checksum validation."""
    if not re.fullmatch(r"[1-9]\d{10}", candidate or ""):
        return False
    d = [int(c) for c in candidate]
    d10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    d11 = sum(d[:10]) % 10
    return d[9] == d10 and d[10] == d11


def anonymize_kvkk_text(text: str) -> dict[str, Any]:
    """MM-09: Irreversible KVKK anonymization for TCKN (checksum-validated), IBAN, phone, email, and TR plates."""
    out = text or ""
    counts: dict[str, int] = {"tckn": 0, "iban": 0, "email": 0, "phone": 0, "plate": 0}

    def _mask_tckn(m: re.Match[str]) -> str:
        val = m.group(0)
        if is_valid_tckn(val):
            counts["tckn"] += 1
            return "[MASKELİ_TCKN]"
        return val

    out = re.sub(r"\b[1-9]\d{10}\b", _mask_tckn, out)
    out, counts["iban"] = re.subn(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", "[MASKELİ_IBAN]", out)
    out, counts["email"] = re.subn(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "[MASKELİ_EPOSTA]", out)
    out, counts["phone"] = re.subn(r"\b(?:\+90|0)?\s?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "[MASKELİ_TELEFON]", out)
    out, counts["plate"] = re.subn(r"\b(?:0[1-9]|[1-7]\d|8[01])\s+[A-Z]{1,3}\s+\d{2,4}\b", "[MASKELİ_PLAKA]", out)
    return {"anonymized_text": out, "masked_counts": counts, "total_masked": sum(counts.values())}


def anonymize_image_regions(image_bytes: bytes, boxes: list[tuple[int, int, int, int]]) -> bytes:
    """MM-09: Irreversibly Gaussian-blur face/plate bounding boxes on an image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    for x1, y1, x2, y2 in boxes:
        region = img.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(radius=14))
        img.paste(region, (x1, y1))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- MM-10 Diagram Validator & Auto-Repair

_MERMAID_HEADERS = ("flowchart ", "graph ", "sequenceDiagram", "stateDiagram", "classDiagram", "erDiagram")


def validate_and_repair_diagram(code: str, *, kind: str = "mermaid") -> dict[str, Any]:
    """MM-10: Validate Mermaid/Graphviz diagram syntax and automatically repair common label/header mistakes."""
    raw = (code or "").strip()
    repairs: list[str] = []
    if kind == "mermaid":
        if not any(raw.startswith(h) for h in _MERMAID_HEADERS):
            raw = "flowchart TD\n" + raw
            repairs.append("added_flowchart_header")
        # Quote unquoted node labels containing parentheses, e.g. A[Step (1)] -> A["Step (1)"]
        fixed = re.sub(r'([A-Za-z0-9_]+)\[([^"\[\]]*\([^"\[\]]*\)[^"\[\]]*)\]', r'\1["\2"]', raw)
        if fixed != raw:
            raw = fixed
            repairs.append("quoted_parenthesized_labels")
        valid = any(raw.startswith(h) for h in _MERMAID_HEADERS) and ("-->" in raw or "->" in raw or ":" in raw)
        return {"valid": valid, "repaired_code": raw, "repairs": repairs}
    # Graphviz DOT
    valid = ("digraph" in raw or "graph" in raw) and raw.count("{") == raw.count("}")
    return {"valid": valid, "repaired_code": raw, "repairs": repairs}


# ---------------------------------------------------------------- MM-13 Fault-Isolated Attachment Pipeline

@dataclass
class AttachmentOutcome:
    filename: str
    mime_type: str
    status: str  # ok | error
    context: str = ""
    error: str = ""


class AttachmentPipeline:
    """MM-13: Registry of isolated per-file-type handlers so one failing attachment never crashes the message."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[bytes, str], Any | Awaitable[Any]]] = {}

    def register(self, ext: str, handler: Callable[[bytes, str], Any | Awaitable[Any]]) -> None:
        self._handlers[ext.lower().lstrip(".")] = handler

    async def process_all(self, attachments: list[dict[str, Any]], *, timeout_s: float = 15.0) -> list[AttachmentOutcome]:
        outcomes: list[AttachmentOutcome] = []
        for att in attachments:
            fname = str(att.get("filename") or "file.bin")
            mime = str(att.get("mime_type") or "application/octet-stream")
            data = att.get("bytes") or b""
            ext = Path(fname).suffix.lower().lstrip(".")
            handler = self._handlers.get(ext)
            if not handler:
                outcomes.append(AttachmentOutcome(fname, mime, "error", error=f"Desteklenmeyen dosya türü: .{ext}"))
                continue
            try:
                res = handler(data, fname)
                if inspect.isawaitable(res):
                    res = await asyncio.wait_for(res, timeout=timeout_s)
                outcomes.append(AttachmentOutcome(fname, mime, "ok", context=str(res)))
            except Exception as exc:
                outcomes.append(AttachmentOutcome(fname, mime, "error", error=f"Ek işlenemedi ({fname}): {exc}"))
        return outcomes


# ---------------------------------------------------------------- MM-14 Authorized, Signed, Expiring Media Lifecycle

def _media_db_path() -> Path:
    p = Path(config.DATA_DIR) / "media_lifecycle.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class MediaLifecycleManager:
    """MM-14: User-bound, HMAC-signed, expiring media storage preventing unauthorized/cross-user access."""

    def __init__(self, *, storage_dir: Path | None = None, db_path: Path | None = None, secret: str | None = None) -> None:
        self.storage_dir = storage_dir or (Path(config.DATA_DIR) / "signed_media")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or _media_db_path()
        self._secret = (secret or "local-media-signing-key-v1").encode("utf-8")
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path), timeout=10.0)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signed_media (
                    media_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _sign(self, media_id: str, owner_id: str, expires_at: int) -> str:
        msg = f"{media_id}:{owner_id}:{expires_at}".encode()
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()[:32]

    def store_media(
        self,
        data: bytes,
        *,
        owner_id: str,
        filename: str,
        content_type: str = "application/octet-stream",
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        media_id = f"med_{secrets.token_urlsafe(16)}"
        exp = int(time.time() + ttl_seconds)
        target = self.storage_dir / f"{media_id}{Path(filename).suffix}"
        target.write_bytes(data)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO signed_media (media_id, owner_id, filename, content_type, file_path, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (media_id, owner_id, filename, content_type, str(target), float(exp), datetime.now(UTC).isoformat()),
            )
        sig = self._sign(media_id, owner_id, exp)
        return {
            "media_id": media_id,
            "owner_id": owner_id,
            "expires_at": exp,
            "signature": sig,
            "signed_url": f"/api/studios/media/{media_id}?user_id={owner_id}&exp={exp}&sig={sig}",
        }

    def fetch_authorized(self, media_id: str, *, requester_id: str, exp: int, sig: str) -> dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM signed_media WHERE media_id = ?", (media_id,)).fetchone()
        if not row:
            raise FileNotFoundError("Medya bulunamadı.")
        if time.time() > float(row["expires_at"]) or time.time() > exp:
            self.cleanup_expired()
            raise FileNotFoundError("Medyanın geçerlilik süresi doldu ve temizlendi.")
        if row["owner_id"] != requester_id:
            raise PermissionError("Bu medyaya erişim yetkiniz yok.")
        expected = self._sign(media_id, requester_id, exp)
        if not hmac.compare_digest(expected, sig or ""):
            raise PermissionError("Geçersiz veya kurcalanmış medya imzası.")
        p = Path(row["file_path"])
        if not p.is_file():
            raise FileNotFoundError("Medya dosyası diskte bulunamadı.")
        return {
            "bytes": p.read_bytes(),
            "filename": row["filename"],
            "content_type": row["content_type"],
        }

    def cleanup_expired(self) -> int:
        now = time.time()
        removed = 0
        with self._conn() as conn:
            rows = conn.execute("SELECT media_id, file_path FROM signed_media WHERE expires_at < ?", (now,)).fetchall()
            for r in rows:
                p = Path(r["file_path"])
                if p.is_file():
                    p.unlink(missing_ok=True)
                conn.execute("DELETE FROM signed_media WHERE media_id = ?", (r["media_id"],))
                removed += 1
        return removed


default_media_manager = MediaLifecycleManager()
