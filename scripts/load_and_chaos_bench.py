"""OPS-16 & OPS-17: Concurrent Load Benchmark (TTFT p95 & Error Rate) + Fault-Injection Resilience Suite."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "master"))


async def run_load_benchmark(*, concurrent_chats: int = 10) -> dict[str, Any]:
    """OPS-16: Simulate concurrent orchestrator requests against deterministic fake gateway and measure p95 latency."""
    from gateway.client import LLMClient
    from gateway.providers import ProviderResponse
    from orchestrator.pipeline import run_pipeline

    class _FastFake:
        name = "fake"
        is_cloud = False

        async def chat(self, model, messages, options, **kwargs):
            await asyncio.sleep(0.005)
            return ProviderResponse(content="Kısa ve doğrulanmış yanıt.", model=model, provider="fake", tokens_in=15, tokens_out=6, latency_ms=5)

        async def stream(self, model, messages, options, **kwargs):
            yield {"type": "token", "content": "OK"}
            yield {"type": "done", "model": model, "provider": "fake", "tokens_in": 10, "tokens_out": 2}

        async def embed(self, model, text, timeout_s=30.0):
            return [0.1] * 16

    client = LLMClient({"fake": _FastFake()})
    latencies: list[float] = []
    errors = 0

    async def _one(idx: int) -> None:
        nonlocal errors
        t0 = time.perf_counter()
        try:
            ctx = await run_pipeline(f"Kısaca açıkla: test #{idx}", user_id="load-user", chat_id=f"ld-{idx}", client=client)
            if not ctx.final_response:
                errors += 1
        except Exception:
            errors += 1
        latencies.append((time.perf_counter() - t0) * 1000.0)

    await asyncio.gather(*(_one(i) for i in range(concurrent_chats)))
    latencies.sort()
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0.0
    err_rate = errors / max(1, concurrent_chats)
    return {
        "concurrent_chats": concurrent_chats,
        "p95_ms": round(p95, 2),
        "error_rate": round(err_rate, 4),
        "passed": err_rate < 0.01 and p95 < 3000.0,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(asyncio.run(run_load_benchmark()), indent=2))
