"""SEC-13: Hardened Docker Container Sandbox Runner.

Enforces defense-in-depth isolation for all untrusted code execution:
- Non-root user (`--user 10001:10001`)
- No network (`--network none`)
- Read-only root filesystem (`--read-only` + bounded noexec `/tmp` tmpfs)
- Dropped Linux capabilities (`--cap-drop ALL`, `--security-opt no-new-privileges:true`)
- Strict seccomp profile (`docker/sandbox/seccomp.json`)
- CPU, memory, and PID limits (`--cpus`, `--memory`, `--pids-limit 64`)
- Single explicit workspace bind mount (`/sandbox`)

When Docker daemon is unavailable, refuses host fallback cleanly and reports the reason
so the UI can display why sandboxed execution is disabled.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MEMORY_LIMIT = "256m"
CPU_LIMIT = "0.5"
PIDS_LIMIT = "64"
TIMEOUT_SECONDS = 10
SANDBOX_IMAGE = "platform-sandbox:latest"
SANDBOX_UID_GID = "10001:10001"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SECCOMP_PATH = _REPO_ROOT / "docker" / "sandbox" / "seccomp.json"
_DOCKERFILE_DIR = _REPO_ROOT / "docker" / "sandbox"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _sandbox_image_present() -> bool:
    try:
        proc = subprocess.run(
            [shutil.which("docker") or "docker", "image", "inspect", SANDBOX_IMAGE],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


def docker_daemon_ready() -> tuple[bool, str]:
    """Check whether Docker CLI exists, daemon is responsive, AND platform-sandbox image is built."""
    if not _docker_available():
        return False, "Docker kurulu değil — güvenli konteyner sandbox kapalı."
    try:
        proc = subprocess.run(
            [shutil.which("docker") or "docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            if not _sandbox_image_present():
                return False, f"Docker {proc.stdout.strip()} aktif ancak `{SANDBOX_IMAGE}` imajı derlenmedi (`docker build -t {SANDBOX_IMAGE} docker/sandbox`)."
            return True, f"Docker {proc.stdout.strip()} aktif"
        return False, "Docker daemon çalışmıyor — güvenli konteyner sandbox kapalı."
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return False, f"Docker erişilemiyor ({exc}) — güvenli konteyner sandbox kapalı."


def status() -> dict[str, Any]:
    ready, reason = docker_daemon_ready()
    return {
        "available": ready,
        "reason": reason,
        "image": SANDBOX_IMAGE,
        "limits": {"memory": MEMORY_LIMIT, "cpus": CPU_LIMIT, "pids": PIDS_LIMIT, "timeout_s": TIMEOUT_SECONDS},
        "seccomp": str(_SECCOMP_PATH) if _SECCOMP_PATH.is_file() else "",
    }


def build_image() -> bool:
    """Build the hardened non-root sandbox Docker image from docker/sandbox/Dockerfile."""
    ready, reason = docker_daemon_ready()
    if not ready:
        log.warning("Sandbox image not built: %s", reason)
        return False
    result = subprocess.run(
        [shutil.which("docker") or "docker", "build", "-t", SANDBOX_IMAGE, str(_DOCKERFILE_DIR)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        log.error("Sandbox image build failed:\n%s", result.stderr)
        return False
    log.info("Sandbox image %s built.", SANDBOX_IMAGE)
    return True


def build_docker_run_args(
    mount_dir: Path,
    command: list[str] | None = None,
    *,
    read_only_mount: bool = True,
    publish_port: tuple[int, int] | None = None,
    timeout_s: int = TIMEOUT_SECONDS,
) -> list[str]:
    """Construct the hardened `docker run` argument vector (never shell=True)."""
    mount_mode = "ro" if read_only_mount else "rw"
    args = [
        "docker",
        "run",
        "--rm",
        "--user",
        SANDBOX_UID_GID,
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--memory",
        MEMORY_LIMIT,
        "--cpus",
        CPU_LIMIT,
        "--pids-limit",
        PIDS_LIMIT,
        "-w",
        "/sandbox",
        "-v",
        f"{Path(mount_dir).resolve()}:/sandbox:{mount_mode}",
    ]
    if _SECCOMP_PATH.is_file():
        args.extend(["--security-opt", f"seccomp={_SECCOMP_PATH.resolve()}"])
    if publish_port is not None:
        host_p, cont_p = publish_port
        args.extend(["-p", f"127.0.0.1:{int(host_p)}:{int(cont_p)}"])
    else:
        args.extend(["--network", "none"])

    args.append(SANDBOX_IMAGE)
    if command:
        args.extend(command)
    return args


def _exec_container(args: list[str], timeout_s: int = TIMEOUT_SECONDS) -> dict[str, Any]:
    ready, reason = docker_daemon_ready()
    if not ready:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": reason,
            "timed_out": False,
            "docker_available": False,
        }
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-6000:],
            "timed_out": False,
            "docker_available": True,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": f"Sandbox zaman aşımına uğradı ({timeout_s} sn).",
            "timed_out": True,
            "docker_available": True,
        }
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
            "docker_available": True,
        }


def run(files: list[dict[str, str]]) -> dict[str, Any]:
    """Run pytest on the provided file list inside the hardened Docker sandbox (PB-41 / SEC-13)."""
    ready, reason = docker_daemon_ready()
    if not ready:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": reason,
            "timed_out": False,
            "docker_available": False,
        }
    with tempfile.TemporaryDirectory(prefix="sandbox_") as tmpdir:
        base = Path(tmpdir).resolve()
        for f in files:
            rel = str(f["path"]).replace("\\", "/").lstrip("/")
            dest = (base / rel).resolve()
            if base != dest and base not in dest.parents:
                raise ValueError(f"Geçersiz sandbox dosya yolu: {rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(str(f["content"]), encoding="utf-8")
        args = build_docker_run_args(base, command=["python", "-m", "pytest", "--tb=short", "-q", "."])
        return _exec_container(args, timeout_s=TIMEOUT_SECONDS)


def run_python_code(code: str, timeout_s: int = TIMEOUT_SECONDS) -> dict[str, Any]:
    """Execute a Python snippet strictly inside the hardened Docker container (never on host)."""
    ready, reason = docker_daemon_ready()
    if not ready:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": reason,
            "timed_out": False,
            "docker_available": False,
        }
    with tempfile.TemporaryDirectory(prefix="sandbox_py_") as tmpdir:
        base = Path(tmpdir).resolve()
        (base / "snippet.py").write_text(code, encoding="utf-8")
        args = build_docker_run_args(base, command=["python", "-I", "/sandbox/snippet.py"])
        return _exec_container(args, timeout_s=timeout_s)


def run_workspace_command(
    ws_dir: Path,
    command: list[str],
    *,
    read_only_mount: bool = True,
    timeout_s: int = TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute a command vector strictly inside the hardened container bound only to `ws_dir`."""
    args = build_docker_run_args(ws_dir, command=command, read_only_mount=read_only_mount, timeout_s=timeout_s)
    return _exec_container(args, timeout_s=timeout_s)
