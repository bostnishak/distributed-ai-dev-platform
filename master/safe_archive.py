"""Upload safety for archives and file types (SEC-07).

Checks an uploaded ZIP before anything is read from it: total unpacked size, file count, compression
ratio, nesting depth, path traversal and symbolic links. File kinds are decided from the first bytes,
not from the name the client chose.
"""

from __future__ import annotations

import io
import posixpath
import stat
import zipfile

MAX_TOTAL_BYTES = 200 * 1024 * 1024
MAX_FILES = 2000
MAX_RATIO = 100
MAX_DEPTH = 2


class UnsafeArchive(ValueError):
    """The archive broke one of the limits; the message says which."""


def _is_link(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(info.external_attr >> 16)


def _check_name(name: str) -> None:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        raise UnsafeArchive(f"mutlak yol reddedildi: {name}")
    if ".." in posixpath.normpath(normalized).split("/"):
        raise UnsafeArchive(f"yol geçişi reddedildi: {name}")


def inspect_zip(raw: bytes, *, depth: int = 0) -> dict[str, int]:
    """Raise UnsafeArchive when the archive is unsafe; otherwise return its size summary."""
    if depth > MAX_DEPTH:
        raise UnsafeArchive(f"iç içe arşiv derinliği {MAX_DEPTH} sınırını aştı")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise UnsafeArchive(f"geçersiz ZIP: {exc}") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise UnsafeArchive(f"dosya sayısı {MAX_FILES} sınırını aştı ({len(infos)})")
        total = 0
        for info in infos:
            _check_name(info.filename)
            if _is_link(info):
                raise UnsafeArchive(f"sembolik bağ reddedildi: {info.filename}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise UnsafeArchive("açılmış toplam boyut 200 MB sınırını aştı")
            if info.compress_size and info.file_size / info.compress_size > MAX_RATIO:
                raise UnsafeArchive(f"sıkıştırma oranı {MAX_RATIO}x sınırını aştı: {info.filename}")
            if info.filename.lower().endswith(".zip") and not info.is_dir():
                with archive.open(info) as inner:
                    inspect_zip(inner.read(MAX_TOTAL_BYTES + 1), depth=depth + 1)
        return {"files": len(infos), "total_bytes": total, "compressed_bytes": len(raw)}


_SIGNATURES = (
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF8", "gif"),
    (b"MZ", "exe"),
    (b"\x7fELF", "elf"),
    (b"PK\x03\x04", "zip"),
)


def sniff_type(head: bytes) -> str:
    """Kind of a file from its leading bytes: pdf, png, jpeg, gif, exe, elf, zip, or text/unknown."""
    for magic, kind in _SIGNATURES:
        if head.startswith(magic):
            return kind
    try:
        head[:512].decode("utf-8")
    except UnicodeDecodeError:
        return "unknown"
    return "text"


def declared_matches_content(filename: str, head: bytes) -> bool:
    """False when the extension claims one kind and the bytes show another (e.g. an .exe renamed .pdf)."""
    kind = sniff_type(head)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if kind in ("exe", "elf"):
        return ext in ("exe", "dll", "so", "bin")
    if ext == "pdf":
        return kind == "pdf"
    if ext in ("png", "jpg", "jpeg", "gif"):
        return kind in ("png", "jpeg", "gif")
    if ext in ("docx", "xlsx", "pptx", "xlsm", "zip"):
        return kind == "zip"
    return True


_PDF_ACTIVE = (b"/JavaScript", b"/JS ", b"/JS(", b"/OpenAction", b"/Launch", b"/AA ", b"/EmbeddedFile")


def scan_active_content(raw: bytes, filename: str = "") -> list[str]:
    """Names of active-content findings (macros, scripts, auto-actions, DDE, external links); empty when clean (SEC-08).

    Nothing is run; the caller indexes the text as plain text and shows the findings as a warning.
    """
    findings: list[str] = []
    kind = sniff_type(raw[:512])
    if kind == "pdf":
        findings += [f"pdf:{marker.decode().strip(' (')}" for marker in _PDF_ACTIVE if marker in raw]
    elif kind == "zip":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for info in archive.infolist():
                    lowered = info.filename.lower()
                    if lowered.endswith("vbaproject.bin"):
                        findings.append("ooxml:vba-macro")
                    elif lowered.endswith(".rels") and info.file_size < 1_000_000:
                        if b'TargetMode="External"' in archive.read(info):
                            findings.append("ooxml:external-link")
                    elif lowered.endswith((".xml", ".xml.rels")) and info.file_size < 5_000_000:
                        body = archive.read(info)
                        if b"DDEAUTO" in body or b"ddeLink" in body:
                            findings.append("ooxml:dde")
        except zipfile.BadZipFile:
            findings.append("zip:corrupt")
    elif filename.lower().endswith((".html", ".htm")) or raw[:512].lstrip().lower().startswith(b"<"):
        if b"<script" in raw.lower():
            findings.append("html:script")
    return sorted(set(findings))
