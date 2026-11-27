"""The explicit agent commands of the chat: deep research and operating a website."""

from __future__ import annotations

from fastapi.responses import StreamingResponse

import browser_agent
import research


def fastpath(prompt: str, has_file: bool) -> StreamingResponse | None:
    return browser_agent.fastpath(prompt, has_file) or research.fastpath(prompt, has_file)
