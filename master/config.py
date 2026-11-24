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

# The Assistant's "Run" button executes Python on the master. The web UI has no login yet
# (PB-56), so anyone who can reach the master could use it; it stays off unless enabled here.
CODE_RUN_ENABLED = os.environ.get("CODE_RUN_ENABLED", "false").strip().lower() in ("1", "true", "yes")

# Maximum tokens generated for the assistant tab (separate from requirements analysis).
ASSISTANT_NUM_PREDICT = int(os.environ.get("ASSISTANT_NUM_PREDICT", "2048"))

# --- Master agent's own local model (used for requirements analysis) ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MASTER_MODEL = os.environ.get("MASTER_MODEL", "qwen3.5:4b")
# Upper bound for the context window requested from Ollama. Larger windows need more RAM
# on a CPU-only machine; documents that do not fit are analyzed in chunks instead.
NUM_CTX_MAX = int(os.environ.get("NUM_CTX_MAX", "32768"))
# Maximum tokens the model may generate for one specification.
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "6144"))
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "1800"))

# Lets a remote caller use the code-running, backup and data-deleting endpoints (see
# access_control.py). Empty means only the master's own machine may use them.
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

# --- Agents ---
# Shared secret every agent sends as "Authorization: Bearer <token>" when registering.
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
# When false, even a request from the master machine needs a signed-in admin session or the admin token (SEC-05).
LOOPBACK_PRIVILEGE = os.environ.get("LOOPBACK_PRIVILEGE", "true").strip().lower() in ("1", "true", "yes")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
BACKUP_PASSWORD = os.environ.get("BACKUP_PASSWORD", "")
REQUIRE_AGENT_APPROVAL = os.environ.get("REQUIRE_AGENT_APPROVAL", "false").strip().lower() in ("1", "true", "yes")
HOST_BIND = os.environ.get("HOST_BIND", "127.0.0.1")
PREVIEW_PORT = int(os.environ.get("PREVIEW_PORT", "8001"))

# --- Storage and limits ---
DB_PATH = Path(os.environ.get("DB_PATH", str(BASE_DIR / "data" / "platform.db")))
# DAT-01: one SQLite file for every module instead of per-module legacy files (see dbunify.py).
UNIFIED_DB = os.environ.get("UNIFIED_DB", "true").strip().lower() in ("1", "true", "yes")
# DAT-07: take an encrypted, verified backup every N hours (0 = off).
BACKUP_INTERVAL_HOURS = float(os.environ.get("BACKUP_INTERVAL_HOURS", "0"))
# OPS-01/18: structured logs, request size cap, housekeeping interval.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_JSON = os.environ.get("LOG_JSON", "true").strip().lower() in ("1", "true", "yes")
MAX_REQUEST_BYTES = int(os.environ.get("MAX_REQUEST_BYTES", str(64 * 1024 * 1024)))
MAINTENANCE_INTERVAL_SECONDS = float(os.environ.get("MAINTENANCE_INTERVAL_SECONDS", "3600"))
DATA_DIR = DB_PATH.parent
CNC_JOBS_DIR = Path(os.environ.get("CNC_JOBS_DIR", str(DATA_DIR / "cnc_jobs")))
WORKSPACES_DIR = Path(os.environ.get("WORKSPACES_DIR", str(DATA_DIR / "workspaces")))
SAMPLES_DIR = BASE_DIR.parent / "samples"


def data_dir() -> Path:
    """DEF-11: Resolve data directory dynamically from current DB_PATH at call time."""
    return Path(DB_PATH).resolve().parent


def workspaces_dir() -> Path:
    """DEF-11: Resolve workspaces directory dynamically from current DB_PATH."""
    return data_dir() / "workspaces"


def cnc_jobs_dir() -> Path:
    """DEF-11: Resolve CNC jobs directory dynamically from current DB_PATH."""
    return data_dir() / "cnc_jobs"

# --- Enterprise AI Models (CNC Ballooning & Project Studio) ---
CNC_VISION_MODEL = os.environ.get("CNC_VISION_MODEL", "cnc-ballooner")
STUDIO_CODER_MODEL = os.environ.get("STUDIO_CODER_MODEL", "qwen2.5-coder:7b")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_CHARS = 300_000
