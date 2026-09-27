"""What the local model can do (read from Ollama) and basic facts about this computer."""

import os
import platform
import socket
from pathlib import Path

import psutil


def parse_show_response(data: dict) -> dict:
    """Extract the registration fields from an Ollama /api/show response."""
    model_info = data.get("model_info") or {}
    architecture = model_info.get("general.architecture")
    context_length = model_info.get(f"{architecture}.context_length") if architecture else None
    if context_length is None:
        context_length = next((v for k, v in model_info.items() if k.endswith(".context_length")), None)
    details = data.get("details") or {}
    return {
        "model_family": details.get("family") or architecture,
        "parameter_size": details.get("parameter_size"),
        "quantization": details.get("quantization_level"),
        "context_length": int(context_length) if context_length else None,
        "capabilities": list(data.get("capabilities") or []),
    }


def collect_host_info() -> dict:
    # Inside Docker the RAM, CPU and OS values describe the Docker VM, not the physical
    # computer, so the runtime is reported too and the UI can say so.
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}".strip(),
        "cpu_count": os.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / 1024**3, 1),
        "runtime": "docker" if Path("/.dockerenv").exists() else "native",
    }
