"""Attachments: size cap, empty and corrupt files are clean 4xx errors."""

import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

import config
from assistant_prep import process_uploaded_attachment

pytestmark = pytest.mark.unit


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=name)


def _status(name: str, data: bytes) -> int:
    with pytest.raises(HTTPException) as err:
        asyncio.run(process_uploaded_attachment(_upload(name, data), "özetle"))
    return err.value.status_code


def test_empty_pdf_is_422():
    assert _status("x.pdf", b"") == 422


def test_corrupt_pdf_is_422_not_500():
    assert _status("x.pdf", b"this is not a pdf at all") == 422


def test_oversized_upload_is_413(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1024)
    assert _status("x.pdf", b"a" * 2048) == 413
