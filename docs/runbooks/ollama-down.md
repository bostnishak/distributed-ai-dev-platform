# Runbook: Ollama Unreachable (`ollama-down`)

## Symptom
- `GET /ready` reports `components.ollama.status = "degraded"` with `"Ollama'ya ulaşılamıyor"`.
- Chat, task decomposition, or agent inference fails with connection refused to `127.0.0.1:11434`.

## Diagnosis
1. Check if Ollama is running:
   ```powershell
   curl.exe -s http://127.0.0.1:11434/api/tags
   ```
2. Verify `OLLAMA_URL` in `.env` (inside Docker Compose, use `http://host.docker.internal:11434`).
3. Inspect local Ollama logs (`%LOCALAPPDATA%\Ollama\server.log` on Windows).

## Resolution
1. Start the Ollama desktop app or run `ollama serve` in a terminal.
2. Re-check `GET http://127.0.0.1:8000/ready` until `components.ollama.status == "ok"`.
3. If VRAM is exhausted by stale models, unload idle models via `ollama stop <model>` or `master/power_manager.py`.
