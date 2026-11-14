"""Register all 6 team member agents, send heartbeats, and pull+execute tasks.

Each agent runs as a coroutine in this process:
  - heartbeat every 10 s
  - poll for tasks every 20 s → submit result via master API

Ollama is called for real tasks; each agent uses the same local Ollama instance.
Run:  python start_agents.py
Stop: Ctrl-C
"""

import asyncio
import logging
import sys
from pathlib import Path

import httpx

MASTER_URL = "http://127.0.0.1:8000"
OLLAMA_URL = "http://127.0.0.1:11434"
HEARTBEAT_INTERVAL = 10   # seconds
TASK_POLL_INTERVAL = 20   # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def _read_token() -> str:
    env_path = Path(__file__).parent / "agent" / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("AGENT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("AGENT_TOKEN bulunamadı — agent/.env dosyasını kontrol edin.")


TOKEN = _read_token()
AUTH = {"Authorization": f"Bearer {TOKEN}"}

MEMBERS = [
    # model = display model shown in UI (team member's "declared" model)
    # execution_model = actually installed model used for Ollama calls
    # capabilities = task types this agent prefers (affects routing scores)
    {
        "agent_id": "uye1", "member_name": "İshak Bostan",
        "model": "qwen3.5:4b", "execution_model": "qwen3.5:4b",
        "capabilities": ["backend", "integration", "coding"],
    },
    {
        "agent_id": "uye2", "member_name": "Zeynep Duru Küçük",
        "model": "phi4-mini", "execution_model": "phi4-mini",
        "capabilities": ["frontend", "documentation", "ui"],
    },
    {
        "agent_id": "uye3", "member_name": "Furkan Kaan Özbeyli",
        "model": "llama3.2:3b", "execution_model": "llama3.2:3b",
        "capabilities": ["testing", "documentation", "review"],
    },
    {
        "agent_id": "uye4", "member_name": "Semih Sarıca",
        "model": "qwen2.5-coder:7b", "execution_model": "qwen2.5-coder:7b",
        "capabilities": ["backend", "database_schema", "coding"],
    },
    {
        "agent_id": "uye5", "member_name": "Işıl Karademir",
        "model": "qwen3.5:9b", "execution_model": "qwen3.5:9b",
        "capabilities": ["documentation", "review", "integration"],
    },
    {
        "agent_id": "uye6", "member_name": "Berfin Yiğit",
        "model": "qwen3:1.7b", "execution_model": "qwen3:1.7b",
        "capabilities": ["frontend", "testing", "documentation"],
    },
]

MODEL_META = {
    "qwen3.5:4b":        {"model_family": "qwen",   "parameter_size": "3.5B", "quantization": "Q4_K_M", "context_length": 32768},
    "phi4-mini":         {"model_family": "phi",    "parameter_size": "3.8B", "quantization": "Q4_K_M", "context_length": 16384},
    "llama3.2:3b":       {"model_family": "llama",  "parameter_size": "3B",   "quantization": "Q4_K_M", "context_length": 8192},
    "qwen2.5-coder:7b":  {"model_family": "qwen",   "parameter_size": "7B",   "quantization": "Q4_K_M", "context_length": 32768},
    "qwen3.5:9b":        {"model_family": "qwen",   "parameter_size": "9B",   "quantization": "Q4_K_M", "context_length": 32768},
    "qwen3:1.7b":        {"model_family": "qwen",   "parameter_size": "1.7B", "quantization": "Q4_K_M", "context_length": 32768},
}

BASE_EXTRAS = {
    "ram_gb": 16.0,
    "cpu_count": 8,
    "os": "Windows 11",
    "agent_version": "0.2.0",
}


async def call_ollama(model: str, prompt: str) -> tuple[str, float | None]:
    """Call local Ollama. Returns (output, tokens_per_second)."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"think": False}},
        )
        resp.raise_for_status()
        data = resp.json()
    output = data.get("response", "")
    eval_count = data.get("eval_count", 0)
    eval_duration_ns = data.get("eval_duration", 1)
    tps = eval_count / (eval_duration_ns / 1e9) if eval_duration_ns > 0 else None
    return output, tps


def _build_prompt(task: dict) -> str:
    """Simple prompt builder for demo tasks."""
    import json
    task_type = task.get("type", "")
    title = task.get("title", "")
    description = task.get("description", "")
    details = task.get("details") or {}

    if task_type == "backend":
        return (
            f"Sen bir Python FastAPI geliştiricisisin.\nGörev: {title}\n{description}\n"
            f"Varlıklar: {json.dumps(details.get('entities',[]), ensure_ascii=False)}\n"
            f"API Uç Noktaları: {json.dumps(details.get('endpoints',[]), ensure_ascii=False)}\n"
            "FastAPI ile bu uç noktaları yaz. Sonucu ```python bloğu içinde ver."
        )
    if task_type == "frontend":
        return (
            f"Sen bir frontend geliştiricisisin.\nGörev: {title}\n{description}\n"
            f"Sayfalar: {json.dumps(details.get('pages',[]), ensure_ascii=False)}\n"
            "HTML/CSS/JS ile bu sayfaları yaz. Sonucu ```frontend/index.html bloğu içinde ver."
        )
    if task_type == "testing":
        return (
            f"Sen bir test uzmanısın.\nGörev: {title}\n{description}\n"
            "Python pytest ile otomatik testler yaz. Sonucu ```python bloğu içinde ver."
        )
    if task_type == "documentation":
        return (
            f"Sen teknik bir yazarsın.\nGörev: {title}\n{description}\n"
            "Markdown formatında proje belgesi yaz. Sonucu ```docs/README.md bloğu içinde ver."
        )
    return f"Görev: {title}\n{description}\n\nBu görevi tamamla ve sonucu yaz."


async def heartbeat_loop(client: httpx.AsyncClient, member: dict, log: logging.Logger) -> None:
    agent_id = member["agent_id"]
    while True:
        try:
            await client.post(
                f"{MASTER_URL}/api/agents/{agent_id}/heartbeat",
                json={"status": "idle"},
                headers=AUTH,
                timeout=5.0,
            )
        except Exception:
            pass
        await asyncio.sleep(HEARTBEAT_INTERVAL)


async def task_loop(client: httpx.AsyncClient, member: dict, log: logging.Logger) -> None:
    agent_id = member["agent_id"]
    model = member["model"]
    # Stagger start so agents don't all poll at exactly the same time
    idx = int(agent_id.replace("uye", "")) - 1
    await asyncio.sleep(idx * 3 + 2)  # uye1→2s, uye2→5s, ..., uye6→17s

    while True:
        try:
            resp = await client.get(
                f"{MASTER_URL}/api/agents/{agent_id}/tasks/next",
                headers=AUTH,
                timeout=10.0,
            )
            if resp.status_code == 204:
                await asyncio.sleep(TASK_POLL_INTERVAL)
                continue
            if resp.status_code != 200:
                await asyncio.sleep(TASK_POLL_INTERVAL)
                continue

            task = resp.json()
            task_id = task.get("id")
            task_type = task.get("type", "")
            log.info("Görev alındı: id=%s type=%s", task_id, task_type)

            # Mark busy
            try:
                await client.post(
                    f"{MASTER_URL}/api/agents/{agent_id}/heartbeat",
                    json={"status": "busy"}, headers=AUTH, timeout=5.0,
                )
            except Exception:
                pass

            # Execute via Ollama (always use the locally installed model)
            exec_model = member.get("execution_model", model)
            prompt = _build_prompt(task)
            try:
                output, tps = await call_ollama(exec_model, prompt)
                log.info("Görev tamamlandı: id=%s (%.0f token/s)", task_id, tps or 0)
            except Exception as exc:
                log.warning("Ollama hatası: %s", exc)
                output = f"HATA: {exc}"
                tps = None

            # Submit result
            try:
                await client.post(
                    f"{MASTER_URL}/api/tasks/{task_id}/result",
                    json={"status": "done", "output": output, "tokens_per_second": tps},
                    headers=AUTH,
                    timeout=10.0,
                )
            except Exception as exc:
                log.warning("Sonuç gönderilemedi: %s", exc)

            # Mark idle again
            try:
                await client.post(
                    f"{MASTER_URL}/api/agents/{agent_id}/heartbeat",
                    json={"status": "idle"}, headers=AUTH, timeout=5.0,
                )
            except Exception:
                pass

            # Poll again quickly after completing a task
            await asyncio.sleep(2)

        except httpx.HTTPError as exc:
            log.debug("Poll hatası: %s", exc)
            await asyncio.sleep(TASK_POLL_INTERVAL)


async def run_member(member: dict) -> None:
    log = logging.getLogger(member["agent_id"])
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Register with display model name + per-model metadata
        meta = MODEL_META.get(member["model"], MODEL_META["qwen3.5:4b"])
        reg_member = {k: v for k, v in member.items() if k not in ("execution_model",)}
        payload = {**BASE_EXTRAS, **meta, **reg_member, "mode": "node"}
        resp = await client.post(f"{MASTER_URL}/api/agents/register", json=payload, headers=AUTH)
        if resp.status_code in (200, 201):
            log.info("Kayıt başarılı: %s", member["member_name"])
        else:
            log.warning("Kayıt hatası: HTTP %s", resp.status_code)

        await asyncio.gather(
            heartbeat_loop(client, member, log),
            task_loop(client, member, log),
        )


async def main() -> None:
    print("=" * 60)
    print("  Dağıtık YZ Platformu — Ajan Başlatıcı")
    print("=" * 60)
    print(f"  Master : {MASTER_URL}")
    print(f"  Ollama : {OLLAMA_URL}")
    print("-" * 60)
    for m in MEMBERS:
        caps = ", ".join(m.get("capabilities", []))
        print(f"  {m['member_name']:<24} model={m['execution_model']:<20} caps=[{caps}]")
    print("=" * 60)
    print("  NOT: Tailscale gerekmez — tüm ajanlar bu makinede çalışır.")
    print("=" * 60)
    await asyncio.gather(*(run_member(m) for m in MEMBERS))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTüm ajanlar durduruldu.")
