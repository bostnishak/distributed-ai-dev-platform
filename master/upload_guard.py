"""Safe handling of chat attachments: size cap, empty files and corrupt documents give clear 4xx errors, never a 500."""

from __future__ import annotations

import zipfile

from fastapi import HTTPException, UploadFile

import config

try:  # pypdf is a dependency of the extractors; keep the guard importable without it
    from pypdf.errors import PyPdfError
except ImportError:  # pragma: no cover
    PyPdfError = ValueError  # type: ignore[misc,assignment]

PARSE_ERRORS = (ValueError, OSError, KeyError, TypeError, RuntimeError, AttributeError, IndexError, EOFError, UnicodeError, zipfile.BadZipFile, PyPdfError)


async def read_limited(file: UploadFile) -> bytes:
    raw = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Dosya çok büyük (en fazla {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")
    if not raw:
        raise HTTPException(status_code=422, detail="Yüklenen dosya boş.")
    return raw


def parse_failure(filename: str) -> HTTPException:
    return HTTPException(status_code=422, detail=f"'{filename}' okunamadı: dosya bozuk ya da desteklenmeyen biçimde.")
