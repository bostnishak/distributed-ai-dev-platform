"""Chat messages handled by a dedicated agent or by code before the general model sees them."""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import arena
import best_of_n
import browser_agent
import confidential
import daemons
import data_chart
import decisions
import dependency_audit
import design_from_image
import doc_reader
import doc_tools
import eda
import federation
import marathon
import math_kernel
import memory_marks
import night_summary
import ops_commands
import os_kernel
import preferences
import project_server
import research
import revise_chat
import science_kernel
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


def _server(prompt: str, history: str) -> str:
    ws_id = revise_chat.last_workspace_id(history)
    return project_server.answer(prompt, wb.safe_workspace_dir(ws_id) if ws_id else None)


def _audit(prompt: str, history: str) -> str:
    ws_id = revise_chat.last_workspace_id(history)
    return dependency_audit.answer(prompt, wb.safe_workspace_dir(ws_id) if ws_id else None, Path(__file__).resolve().parent)


def _decision(prompt: str, history: str) -> str:
    ws_id = revise_chat.last_workspace_id(history)
    ws_dir = wb.safe_workspace_dir(ws_id) if ws_id else None
    if reply := decisions.answer(prompt, ws_dir):
        return reply
    decisions.note(prompt, ws_dir)  # a decision inside an ordinary request is recorded; the request goes on
    return ""


def _command(prompt: str, history: str) -> str:
    """Answers computed by code alone."""
    return (preferences.command(prompt) or ops_commands.answer(prompt) or daemons.answer(prompt) or os_kernel.answer(prompt) or federation.answer(prompt)
            or _states(prompt, history) or _server(prompt, history) or _audit(prompt, history) or night_summary.answer(prompt) or _decision(prompt, history) or memory_marks.answer(prompt) or science_kernel.answer(prompt) or math_kernel.answer(prompt))


def _agents(prompt: str, history: str) -> StreamingResponse | None:
    return (marathon.fastpath(prompt) or tts.fastpath(prompt, history) or arena.fastpath(prompt) or self_play.fastpath(prompt) or best_of_n.fastpath(prompt)
            or swarm.fastpath(prompt, history))


def fastpath(prompt: str, file: UploadFile | None, history: str = "") -> StreamingResponse | None:
    if file is not None and file.filename:
        return doc_tools.fastpath(prompt, file) or design_from_image.fastpath(prompt, file) or data_chart.fastpath(prompt, file) or eda.fastpath(prompt, file) or doc_reader.fastpath(prompt, file)
    if reply := confidential.observe(prompt):
        import assistant_stream_fastpaths as fp

        return fp.single_token_stream(reply, "kod", "gizlilik")
    preferences.remember(prompt)
    if result := _command(prompt, history):
        import assistant_stream_fastpaths as fp

        return fp.single_token_stream(result, "kod", "hesaplama")
    return _agents(prompt, history) or variants.fastpath(prompt, history) or browser_agent.fastpath(prompt, False) or workspace_commands.fastpath(prompt, history) or research.fastpath(prompt, False)
