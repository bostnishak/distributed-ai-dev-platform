"""Agent that runs on each team member's computer, next to that member's Ollama model.

Sprint 1: on start-up the agent reads what its local model can do from Ollama and registers
with the master. It only ever opens outbound connections (pull model): nothing on this
computer has to accept incoming connections, and Ollama keeps listening on localhost only.
Heartbeats (Sprint 2) and pulling tasks from the master (Sprint 3) will extend run().
"""

import asyncio
import logging
import os
import sys
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

from model_info import collect_host_info, parse_show_response

AGENT_VERSION = "0.1.0"
REQUIRED_SETTINGS = ("AGENT_ID", "MEMBER_NAME", "MODEL", "MASTER_URL", "AGENT_TOKEN")
RETRY_DELAYS = (2, 4, 8, 15, 30, 60)

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
        log.info("Ajan açık bekliyor. Görev çekme ve yürütme Sprint 3'te eklenecek; bu pencereyi kapatmayın.")
        while True:
            await sleep(3600)
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
