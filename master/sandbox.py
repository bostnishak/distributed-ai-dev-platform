"""Sandboxed code execution via Docker (PB-41).

Runs Python files in a network-isolated Docker container with memory, CPU
and time limits so that generated code cannot harm the host.

If Docker is not available the runner falls back to a no-exec path and returns
a failure result — this lets tests and CI pass on machines without Docker.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

log = logging.getLogger(__name__)

# Container limits (can be overridden by environment variables through config)
MEMORY_LIMIT = "256m"
CPU_LIMIT = "0.5"
TIMEOUT_SECONDS = 30
SANDBOX_IMAGE = "platform-sandbox:latest"

_DOCKERFILE = textwrap.dedent("""\
    FROM python:3.12-slim
    WORKDIR /sandbox
    # No pip install — generated tests should only use stdlib
    CMD ["python", "-m", "pytest", "--tb=short", "-q", "."]
""")


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def build_image() -> bool:
    """Build the sandbox Docker image if Docker is available. Returns True on success."""
    if not _docker_available():
        log.warning("Docker not found — sandbox image not built.")
        return False
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "Dockerfile").write_text(_DOCKERFILE, encoding="utf-8")
        result = subprocess.run(
            ["docker", "build", "-t", SANDBOX_IMAGE, tmpdir],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            log.error("sandbox image build failed:\n%s", result.stderr)
            return False
    log.info("Sandbox image %s built.", SANDBOX_IMAGE)
    return True


def run(files: list[dict]) -> dict:
    """Run the given file set inside a Docker sandbox.

    Args:
        files: list of {"path": str, "content": str} dicts.

    Returns:
        {
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "timed_out": bool,
            "docker_available": bool,
        }
    """
    if not _docker_available():
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Docker not available on this host — sandbox skipped.",
            "timed_out": False,
            "docker_available": False,
        }

    with tempfile.TemporaryDirectory(prefix="sandbox_") as tmpdir:
        # Write all files into the temp directory
        for f in files:
            dest = Path(tmpdir) / f["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f["content"], encoding="utf-8")

        try:
            proc = subprocess.run(
                [
                    "docker", "run",
                    "--rm",
                    "--network", "none",
                    "--memory", MEMORY_LIMIT,
                    "--cpus", CPU_LIMIT,
                    "-v", f"{tmpdir}:/sandbox:ro",
                    SANDBOX_IMAGE,
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS + 5,
            )
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "docker_available": True,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Sandbox timed out after {TIMEOUT_SECONDS}s.",
                "timed_out": True,
                "docker_available": True,
            }
        except Exception as exc:
            log.exception("Sandbox run error: %s", exc)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "timed_out": False,
                "docker_available": True,
            }
