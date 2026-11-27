"""Chat messages handled by a dedicated agent or by code before the general model sees them."""

from __future__ import annotations

from fastapi.responses import StreamingResponse

import browser_agent
import math_kernel
import research
import workspace_commands


def fastpath(prompt: str, has_file: bool, history: str = "") -> StreamingResponse | None:
    if has_file:
        return None
    if result := math_kernel.answer(prompt):
        import assistant_stream_fastpaths as fp

        return fp.single_token_stream(result, "sympy", "hesaplama")
    return browser_agent.fastpath(prompt, has_file) or workspace_commands.fastpath(prompt, history) or research.fastpath(prompt, has_file)
