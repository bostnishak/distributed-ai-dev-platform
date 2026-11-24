"""Pydantic request schemas for `productivity_api.py`."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TextBody(BaseModel):
    text: str = Field(..., max_length=100_000)


class ProjectInstructionBody(BaseModel):
    project_instructions: str = Field(..., max_length=8000)


class RegexTestBody(BaseModel):
    pattern: str = Field(..., max_length=500)
    text: str = Field(..., max_length=50_000)
    flags: str = ""


class CodeTranslateBody(BaseModel):
    code: str
    source_lang: str = "python"
    target_lang: str = "javascript"


class TableRowsBody(BaseModel):
    rows: list[dict[str, Any]]
    row_key: str = ""
    col_key: str = ""
    value_key: str = ""
    fill_value: Any = 0


class IcsEventBody(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    description: str = ""
    location: str = ""


class CustomAgentBody(BaseModel):
    name: str
    instructions: str
    model: str = "qwen3.5:4b"
    tools: list[str] = Field(default_factory=list)


class ScheduleJobBody(BaseModel):
    name: str
    cron: str = "0 9 * * *"
    prompt: str


class ApprovalBody(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GeocodeBody(BaseModel):
    lat1: float
    lon1: float
    lat2: float
    lon2: float


class MailMergeBody(BaseModel):
    template: str
    records: list[dict[str, Any]]


class SurveyBody(BaseModel):
    title: str
    fields: list[dict[str, Any]]


class TranslateQueryBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    target: str = "en"


class AudioConvertBody(BaseModel):
    wav_base64: str = Field(..., min_length=16)
    normalize: bool = True
    trim_silence: bool = True
    target_rate: int = 16000
    mono: bool = True


class VideoGenerateBody(BaseModel):
    slides: list[dict[str, Any]] = Field(default_factory=list)
    width: int = 480
    height: int = 270
    frame_ms: int = 900


class SourceDownloadBody(BaseModel):
    url: str = Field(..., min_length=8, max_length=1024)
    title: str = ""
    content_base64: str = ""
    content_text: str = ""
    is_pdf: bool = False


class ApprovalDecisionBody(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    reviewer: str = "admin"
    note: str = ""


class ConnectorScanBody(BaseModel):
    path: str = ""
    limit: int = 20
