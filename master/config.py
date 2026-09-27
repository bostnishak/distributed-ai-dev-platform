"""Runtime settings for the master service.

Values come from environment variables (Docker Compose sets them) or from the repo-level
.env file during local development. Other modules read them as ``config.NAME`` at call time
so tests can override them with monkeypatch.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# The single .env file lives at the repo root (one level above this service).
load_dotenv(BASE_DIR.parent / ".env")

# --- Assistant tab (still served through the LiteLLM gateway until Sprint 3) ---
GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://localhost:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY")

# --- Master agent's own local model (used for requirements analysis) ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MASTER_MODEL = os.environ.get("MASTER_MODEL", "qwen3.5:4b")
# Upper bound for the context window requested from Ollama. Larger windows need more RAM
# on a CPU-only machine; documents that do not fit are analyzed in chunks instead.
NUM_CTX_MAX = int(os.environ.get("NUM_CTX_MAX", "32768"))
# Maximum tokens the model may generate for one specification.
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "6144"))
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "1800"))

# --- Agents ---
# Shared secret every agent sends as "Authorization: Bearer <token>" when registering.
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")

# --- Storage and limits ---
DB_PATH = Path(os.environ.get("DB_PATH", str(BASE_DIR / "data" / "platform.db")))
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DOCUMENT_CHARS = 300_000
