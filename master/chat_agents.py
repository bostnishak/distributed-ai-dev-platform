"""Chat messages handled by a dedicated agent or by code before the general model sees them."""

from __future__ import annotations

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import arena
import best_of_n
import browser_agent
import daemons
import data_chart
import design_from_image
import doc_reader
import eda
import federation
import math_kernel
import ops_commands
import preferences
import research
import revise_chat
import self_play
import statecheck
import swarm
import tts
import variants
import workspace_builder as wb
import workspace_commands


def _states(prompt: str, history: str) -> str:
    ws_id = revise_chat.last_workspace_id(history)
    return statecheck.answer(prompt, wb.safe_workspace_dir(ws_id) if ws_id else None)


def _command(prompt: str, history: str) -> str:
    """Answers computed by code alone."""
    return (preferences.command(prompt) or ops_commands.answer(prompt) or daemons.answer(prompt) or federation.answer(prompt)
            or _states(prompt, history) or math_kernel.answer(prompt))


def _agents(prompt: str, history: str) -> StreamingResponse | None:
    return (tts.fastpath(prompt, history) or arena.fastpath(prompt) or self_play.fastpath(prompt) or best_of_n.fastpath(prompt)
            or swarm.fastpath(prompt, history))


def fastpath(prompt: str, file: UploadFile | None, history: str = "") -> StreamingResponse | None:
    if file is not None and file.filename:
        return design_from_image.fastpath(prompt, file) or data_chart.fastpath(prompt, file) or eda.fastpath(prompt, file) or doc_reader.fastpath(prompt, file)
    preferences.remember(prompt)
    if result := _command(prompt, history):
        import assistant_stream_fastpaths as fp

        return fp.single_token_stream(result, "kod", "hesaplama")
    return _agents(prompt, history) or variants.fastpath(prompt) or browser_agent.fastpath(prompt, False) or workspace_commands.fastpath(prompt, history) or research.fastpath(prompt, False)
