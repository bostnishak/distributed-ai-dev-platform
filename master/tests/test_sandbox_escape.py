"""SEC-13: Real Docker Container Sandbox Escape Tests (`pytest -m security`).

Runs automatically when Docker daemon + `platform-sandbox:latest` image are available;
otherwise verifies that `sandbox` fails closed cleanly without falling back to host execution.
"""

from __future__ import annotations

import subprocess

import pytest

import sandbox

pytestmark = pytest.mark.security


def _sandbox_image_present() -> bool:
    ready, _ = sandbox.docker_daemon_ready()
    if not ready:
        return False
    proc = subprocess.run(
        ["docker", "image", "inspect", sandbox.SANDBOX_IMAGE],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return proc.returncode == 0


def test_sec13_fail_closed_when_docker_unavailable(monkeypatch):
    monkeypatch.setattr(sandbox, "docker_daemon_ready", lambda: (False, "Docker test kapalı"))
    from sandbox import runner

    monkeypatch.setattr(runner, "docker_daemon_ready", lambda: (False, "Docker test kapalı"))
    res = sandbox.run_python_code("print('SHOULD_NOT_RUN_ON_HOST')")
    assert res["docker_available"] is False
    assert res["ok"] is False
    assert "SHOULD_NOT_RUN_ON_HOST" not in res["stdout"]


@pytest.mark.skipif(not _sandbox_image_present(), reason="Docker daemon or platform-sandbox:latest image not available")
def test_sec13_container_blocks_network_readonly_root_and_fork_bomb():
    # 1. Network isolated (--network none)
    net_res = sandbox.run_python_code(
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000', timeout=2)"
    )
    assert net_res["exit_code"] != 0

    # 2. Root filesystem /etc is read-only
    ro_res = sandbox.run_python_code("open('/etc/pwned', 'w').write('x')")
    assert ro_res["exit_code"] != 0

    # 3. Fork bomb stopped within 10s by --pids-limit / timeout
    fb_res = sandbox.run_python_code("import os\nwhile True:\n    os.fork()", timeout_s=10)
    assert fb_res["exit_code"] != 0 or fb_res["timed_out"] is True
