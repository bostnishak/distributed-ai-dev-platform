"""Route fresh Excel/Word/PDF requests to the flow that designs the file for the request."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import doc_flow
import xlsx_flow

FORMATS = ("xlsx", "docx", "pdf")


async def generate(prompt: str, fmt: str, ctx: tuple[str, str], out_path: Path, helpers: tuple[Any, Any]) -> dict[str, Any]:
    """`ctx` = (target language, model); `helpers` = (JSON extractor, (regular font, bold font))."""
    target_lang, model = ctx
    if fmt == "xlsx":
        return await xlsx_flow.generate(prompt, target_lang, model, out_path)
    return await doc_flow.generate(prompt, fmt, ctx, out_path, helpers)
