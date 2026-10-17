"""Agent that runs on each team member's computer, next to that member's Ollama model.

Sprint 1: on start-up the agent reads what its local model can do from Ollama and registers
with the master.
Sprint 2: heartbeat loop (every 10s) and task-pull loop (every 30s) run concurrently.
Pull model: the agent only ever opens outbound connections; nothing on this computer has to
accept incoming connections, and Ollama keeps listening on localhost only.
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

from model_info import collect_host_info, parse_show_response

AGENT_VERSION = "0.2.0"
REQUIRED_SETTINGS = ("AGENT_ID", "MEMBER_NAME", "MODEL", "MASTER_URL", "AGENT_TOKEN")
RETRY_DELAYS = (2, 4, 8, 15, 30, 60)
HEARTBEAT_INTERVAL = 10   # seconds
TASK_PULL_INTERVAL = 30   # seconds

log = logging.getLogger("agent")


class ConfigError(RuntimeError):
    pass


class FatalError(RuntimeError):
    """A failure that retrying cannot fix (wrong token, missing model, wrong master URL)."""


@dataclass(frozen=True)
class Settings:
    agent_id: str
    member_name: str
    model: str
    master_url: str
    agent_token: str
    ollama_url: str
    mode: str


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    missing = [name for name in REQUIRED_SETTINGS if not env.get(name, "").strip()]
    if missing:
        raise ConfigError(
            f"Eksik ayar: {', '.join(missing)}. agent/.env dosyasını kontrol edin "
            "(bkz. agent-node/README.md)."
        )
    mode = env.get("AGENT_MODE", "node").strip() or "node"
    if mode not in ("node", "staging"):
        raise ConfigError("AGENT_MODE 'node' ya da 'staging' olmalı.")
    return Settings(
        agent_id=env["AGENT_ID"].strip(),
        member_name=env["MEMBER_NAME"].strip(),
        model=env["MODEL"].strip(),
        master_url=env["MASTER_URL"].strip().rstrip("/"),
        agent_token=env["AGENT_TOKEN"].strip(),
        ollama_url=(env.get("OLLAMA_URL") or "http://127.0.0.1:11434").strip().rstrip("/"),
        mode=mode,
    )


def _describe(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
    return type(exc).__name__


async def fetch_model_info(client: httpx.AsyncClient, settings: Settings) -> dict:
    resp = await client.post(f"{settings.ollama_url}/api/show", json={"model": settings.model})
    if resp.status_code == 404:
        raise FatalError(
            f"'{settings.model}' modeli bu bilgisayarda yüklü değil. Önce şunu çalıştırın: "
            f"ollama pull {settings.model}"
        )
    resp.raise_for_status()
    return parse_show_response(resp.json())


def build_registration(settings: Settings, model_info: dict, host_info: dict) -> dict:
    return {
        "agent_id": settings.agent_id,
        "member_name": settings.member_name,
        "model": settings.model,
        "mode": settings.mode,
        **host_info,
        **model_info,
        "agent_version": AGENT_VERSION,
    }


async def register(client: httpx.AsyncClient, settings: Settings, payload: dict) -> dict:
    resp = await client.post(
        f"{settings.master_url}/api/agents/register",
        json=payload,
        headers={"Authorization": f"Bearer {settings.agent_token}"},
    )
    if resp.status_code == 401:
        raise FatalError(
            "Master AGENT_TOKEN'ı reddetti. agent/.env içindeki AGENT_TOKEN'ı master'ı "
            "çalıştıran kişiden aldığınız değerle karşılaştırın."
        )
    if resp.status_code == 404:
        raise FatalError(f"MASTER_URL adresinde master bulunamadı: {settings.master_url}")
    if resp.status_code == 422:
        raise FatalError(f"Master kayıt bilgilerini geçersiz buldu: {resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()


async def with_retry(
    action: Callable[[], Awaitable[dict]],
    what: str,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict:
    """Retry network failures with growing delays; FatalError is raised immediately."""
    attempt = 0
    while True:
        try:
            return await action()
        except httpx.HTTPError as exc:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            log.warning("%s başarısız (%s). %s sn sonra tekrar denenecek.", what, _describe(exc), delay)
            attempt += 1
            await sleep(delay)


# ---------------------------------------------------------------------------
# Sprint 2: heartbeat loop
# ---------------------------------------------------------------------------

async def heartbeat_loop(
    settings: Settings,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Send a heartbeat to master every HEARTBEAT_INTERVAL seconds."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                resp = await client.post(
                    f"{settings.master_url}/api/agents/{settings.agent_id}/heartbeat",
                    json={"status": "idle"},
                    headers={"Authorization": f"Bearer {settings.agent_token}"},
                )
                if resp.status_code not in (200, 204):
                    log.warning("Heartbeat rejected: HTTP %s", resp.status_code)
            except httpx.HTTPError as exc:
                log.debug("Heartbeat failed: %s", _describe(exc))
            await sleep(HEARTBEAT_INTERVAL)


# ---------------------------------------------------------------------------
# Sprint 2: task execution helpers
# ---------------------------------------------------------------------------

async def call_ollama(settings: Settings, prompt: str) -> tuple[str, float]:
    """Call local Ollama with the given prompt. Returns (output, tokens_per_second)."""
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.model,
                "prompt": prompt,
                "stream": False,
                "options": {"think": False},
            },
        )
        resp.raise_for_status()
        data = resp.json()
    elapsed = time.monotonic() - start
    output = data.get("response", "")
    eval_count = data.get("eval_count", 0)
    eval_duration_ns = data.get("eval_duration", 0)
    if eval_duration_ns > 0:
        tps = eval_count / (eval_duration_ns / 1e9)
    elif elapsed > 0 and len(output) > 0:
        tps = len(output.split()) / elapsed  # rough estimate
    else:
        tps = 0.0
    return output, tps


async def execute_task(settings: Settings, task: dict) -> tuple[str, float | None]:
    """Execute a task and return (output, tokens_per_second)."""
    task_type = task.get("type", "")
    details = task.get("details") or {}

    if task_type == "benchmark":
        # Run the first benchmark question as the task prompt
        from benchmarks import BENCHMARK_BY_ID, BENCHMARKS_BY_DIMENSION  # type: ignore[import]
        benchmark_ids = details.get("benchmark_ids", [])
        if not benchmark_ids:
            bid = details.get("benchmark_id")
            if bid:
                benchmark_ids = [bid]
        if benchmark_ids:
            first_b = BENCHMARK_BY_ID.get(benchmark_ids[0])
            if first_b:
                question = first_b["question"]
                try:
                    output, tps = await call_ollama(settings, question)
                    return output, tps
                except Exception as exc:
                    log.warning("Ollama call failed for benchmark: %s", exc)
                    return f"ERROR: {exc}", None
        return "No benchmark found", None
    else:
        # Non-benchmark tasks: placeholder until Sprint 3
        return "Sprint 3'te implement edilecek.", None


# ---------------------------------------------------------------------------
# Sprint 2: task pull loop
# ---------------------------------------------------------------------------

async def task_pull_loop(
    settings: Settings,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Poll master for tasks every TASK_PULL_INTERVAL seconds and execute them."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                resp = await client.get(
                    f"{settings.master_url}/api/agents/{settings.agent_id}/tasks/next",
                    headers={"Authorization": f"Bearer {settings.agent_token}"},
                )
                if resp.status_code == 204:
                    pass  # No task available
                elif resp.status_code == 200:
                    task = resp.json()
                    task_id = task.get("id")
                    log.info("Task received: id=%s type=%s", task_id, task.get("type"))

                    # Mark busy via heartbeat
                    try:
                        await client.post(
                            f"{settings.master_url}/api/agents/{settings.agent_id}/heartbeat",
                            json={"status": "busy"},
                            headers={"Authorization": f"Bearer {settings.agent_token}"},
                        )
                    except Exception:
                        pass

                    output, tps = await execute_task(settings, task)
                    status = "done"

                    # Submit result
                    try:
                        result_resp = await client.post(
                            f"{settings.master_url}/api/tasks/{task_id}/result",
                            json={
                                "status": status,
                                "output": output,
                                "tokens_per_second": tps,
                            },
                            headers={"Authorization": f"Bearer {settings.agent_token}"},
                        )
                        if result_resp.status_code == 200:
                            log.info("Task %s result submitted.", task_id)
                        else:
                            log.warning("Result submission failed: HTTP %s", result_resp.status_code)
                    except httpx.HTTPError as exc:
                        log.warning("Result submission error: %s", _describe(exc))

                    # Mark idle again
                    try:
                        await client.post(
                            f"{settings.master_url}/api/agents/{settings.agent_id}/heartbeat",
                            json={"status": "idle"},
                            headers={"Authorization": f"Bearer {settings.agent_token}"},
                        )
                    except Exception:
                        pass

                else:
                    log.warning("Unexpected status from tasks/next: %s", resp.status_code)
            except httpx.HTTPError as exc:
                log.debug("Task poll failed: %s", _describe(exc))

            await sleep(TASK_PULL_INTERVAL)


# ---------------------------------------------------------------------------
# Main run loop
# ---------------------------------------------------------------------------

async def run(
    settings: Settings,
    client: httpx.AsyncClient | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    stay_running: bool = True,
) -> dict:
    async with client or httpx.AsyncClient(timeout=30.0) as http:
        model_info = await with_retry(lambda: fetch_model_info(http, settings), "Ollama'dan model bilgisi alma", sleep)
        payload = build_registration(settings, model_info, collect_host_info())
        agent = await with_retry(lambda: register(http, settings, payload), "Master'a kayıt", sleep)

    log.info(
        "Master'a kaydolundu: %s (%s, bağlam %s token, yetenekler: %s).",
        agent["agent_id"], agent["model"], agent.get("context_length"), ", ".join(agent["capabilities"]),
    )
    if stay_running:
        log.info("Heartbeat ve görev çekme döngüleri başlatılıyor.")
        await asyncio.gather(
            heartbeat_loop(settings, sleep),
            task_pull_loop(settings, sleep),
        )
    return agent


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    # httpx logs every request at INFO; members only need the agent's own messages.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv(Path(__file__).resolve().parent / ".env")
    try:
        settings = load_settings()
    except ConfigError as exc:
        log.error("%s", exc)
        sys.exit(2)
    log.info("Ajan başlıyor: %s (%s), master: %s", settings.agent_id, settings.model, settings.master_url)
    try:
        asyncio.run(run(settings))
    except FatalError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Ajan durduruldu.")


if __name__ == "__main__":
    main()
