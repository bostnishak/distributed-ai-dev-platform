import asyncio
import json
import re

import httpx
import pytest

import agent
from agent import ConfigError, FatalError, Settings, load_settings, run

SETTINGS = Settings(
    agent_id="uye5", member_name="Işıl Karademir", model="qwen2.5-coder:7b",
    master_url="http://master:8000", agent_token="secret", ollama_url="http://ollama:11434", mode="staging",
)
SHOW = {
    "capabilities": ["completion", "tools", "insert"],
    "details": {"family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
    "model_info": {"general.architecture": "qwen2", "qwen2.context_length": 32768},
}


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def no_sleep(_seconds):
    return None


def registered_echo(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    return httpx.Response(200, json={**payload, "registered_at": "t", "last_seen_at": "t"})


class TestLoadSettings:
    def test_reports_all_missing_settings(self):
        with pytest.raises(ConfigError) as exc:
            load_settings({"AGENT_ID": "uye1"})
        assert "MEMBER_NAME" in str(exc.value) and "AGENT_TOKEN" in str(exc.value)

    def test_defaults_and_trimming(self):
        settings = load_settings({
            "AGENT_ID": "uye1", "MEMBER_NAME": "İshak Bostan", "MODEL": "qwen3.5:4b",
            "MASTER_URL": "http://ishak-pc:8000/", "AGENT_TOKEN": " t ",
        })
        assert settings.master_url == "http://ishak-pc:8000"
        assert settings.agent_token == "t"
        assert settings.ollama_url == "http://127.0.0.1:11434"
        assert settings.mode == "node"

    def test_rejects_unknown_mode(self):
        with pytest.raises(ConfigError):
            load_settings({
                "AGENT_ID": "a", "MEMBER_NAME": "b", "MODEL": "c", "MASTER_URL": "d",
                "AGENT_TOKEN": "e", "AGENT_MODE": "cloud",
            })


def test_registers_with_model_capabilities():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json=SHOW)
        seen["auth"] = request.headers["authorization"]
        return registered_echo(request)

    result = asyncio.run(run(SETTINGS, client=make_client(handler), sleep=no_sleep, stay_running=False))
    assert seen["auth"] == "Bearer secret"
    assert result["agent_id"] == "uye5"
    assert result["mode"] == "staging"
    assert result["context_length"] == 32768
    assert result["capabilities"] == ["completion", "tools", "insert"]
    assert result["agent_version"] == agent.AGENT_VERSION
    assert result["ram_gb"] > 0


def test_retries_until_master_is_reachable():
    attempts = {"register": 0}
    delays = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json=SHOW)
        attempts["register"] += 1
        if attempts["register"] < 3:
            raise httpx.ConnectError("master is down")
        return registered_echo(request)

    async def record_sleep(seconds):
        delays.append(seconds)

    asyncio.run(run(SETTINGS, client=make_client(handler), sleep=record_sleep, stay_running=False))
    assert attempts["register"] == 3
    assert delays == [2, 4]


def test_retries_server_errors():
    attempts = {"register": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json=SHOW)
        attempts["register"] += 1
        if attempts["register"] == 1:
            return httpx.Response(503, json={"detail": "AGENT_TOKEN ayarlanmamış"})
        return registered_echo(request)

    asyncio.run(run(SETTINGS, client=make_client(handler), sleep=no_sleep, stay_running=False))
    assert attempts["register"] == 2


def test_wrong_token_is_fatal():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json=SHOW)
        return httpx.Response(401, json={"detail": "Geçersiz ajan anahtarı"})

    with pytest.raises(FatalError, match="AGENT_TOKEN"):
        asyncio.run(run(SETTINGS, client=make_client(handler), sleep=no_sleep, stay_running=False))


def test_missing_model_is_fatal():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(FatalError, match=re.escape("ollama pull qwen2.5-coder:7b")):
        asyncio.run(run(SETTINGS, client=make_client(handler), sleep=no_sleep, stay_running=False))
