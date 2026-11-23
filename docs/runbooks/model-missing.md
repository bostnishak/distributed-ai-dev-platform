# Runbook: Required Model Missing (`model-missing`)

## Symptom
- `GET /ready` reports `components.ollama.status = "degraded"` with `"<model> modeli yüklü değil"`.
- `scripts/rag_doctor.py` warns that `bge-m3` is missing.

## Diagnosis
1. List installed models:
   ```powershell
   ollama list
   ```
2. Compare against `MASTER_MODEL` (default `qwen3.5:4b`) and embedding model `bge-m3`.

## Resolution
1. Pull missing models:
   ```powershell
   ollama pull qwen3.5:4b
   ollama pull bge-m3
   ```
2. Re-run `GET http://127.0.0.1:8000/ready` and `.\master\venv\Scripts\python.exe scripts/rag_doctor.py`.
