"""Chat messages handled by a dedicated agent or by code before the general model sees them."""

from __future__ import annotations

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import browser_agent
import data_chart
import design_from_image
import doc_reader
import eda
import math_kernel
import ops_commands
import preferences
import research
import variants
import workspace_commands


def fastpath(prompt: str, file: UploadFile | None, history: str = "") -> StreamingResponse | None:
    if file is not None and file.filename:
        return design_from_image.fastpath(prompt, file) or data_chart.fastpath(prompt, file) or eda.fastpath(prompt, file) or doc_reader.fastpath(prompt, file)
    preferences.remember(prompt)
    if result := preferences.command(prompt) or ops_commands.answer(prompt) or math_kernel.answer(prompt):
        import assistant_stream_fastpaths as fp

        return fp.single_token_stream(result, "kod", "hesaplama")
    return variants.fastpath(prompt) or browser_agent.fastpath(prompt, False) or workspace_commands.fastpath(prompt, history) or research.fastpath(prompt, False)
