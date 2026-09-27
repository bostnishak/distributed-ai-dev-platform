#!/usr/bin/env bash
# Starts the agent that setup.sh installed. Keep the terminal open while you want your
# computer to take part in the platform.
set -euo pipefail
AGENT_DIR="$(cd "$(dirname "$0")/../agent" && pwd)"
if [ ! -x "$AGENT_DIR/.venv/bin/python" ]; then
  echo "Ajan kurulu degil. Once: ./agent-node/setup.sh <uyeN>"
  exit 1
fi
exec "$AGENT_DIR/.venv/bin/python" "$AGENT_DIR/agent.py"
