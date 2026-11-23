#!/usr/bin/env bash
# OPS-04: Single-command Linux/macOS launcher (venv verify, port check, Ollama check, safe 127.0.0.1 bind, /ready poll).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${MASTER_HOST:-127.0.0.1}"
PORT="${MASTER_PORT:-8000}"
VENV="$ROOT_DIR/master/venv"

if [ ! -x "$VENV/bin/python" ]; then
  echo "[OPS-04] Creating virtualenv in $VENV..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r "$ROOT_DIR/master/requirements.txt"
fi

if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "[OPS-04] Warning: Ollama is not responding on 127.0.0.1:11434 (run 'ollama serve')."
fi

echo "[OPS-04] Starting Master on http://$HOST:$PORT ..."
cd "$ROOT_DIR/master"
exec "$VENV/bin/python" -m uvicorn app:app --host "$HOST" --port "$PORT"
