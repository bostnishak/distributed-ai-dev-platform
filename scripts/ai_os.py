"""Local launch kernel: doctor (hardware and dependencies), up (start the core only), unload (free GPU memory), bench.

Usage: python scripts/ai_os.py doctor | up [--port 8000] [--lan] | unload | bench | export-training [dir] | import-gguf <file>
Heavy parts (Docker sandbox, headless browser) start only when a task needs them and exit with it.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "master"))
import config  # noqa: E402
import training_pack  # noqa: E402
import visual_audit  # noqa: E402

PROFILES = (("WORKSTATION_48GB+", 32_000), ("PRO_16_24GB", 12_000), ("NANO_8GB", 0))


def _out(args, timeout=15):
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def vram_mb():
    values = [int(v) for v in _out(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]).split() if v.isdigit()]
    return max(values, default=0)


def profile_for(vram):
    return next(name for name, floor in PROFILES if vram >= floor)


def ollama_models():
    try:
        return [m["name"] for m in httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=5).json().get("models", [])]
    except (httpx.HTTPError, ValueError, KeyError):
        return None


OLLAMA_SETTINGS = (("OLLAMA_FLASH_ATTENTION", "1"), ("OLLAMA_KV_CACHE_TYPE", "q8_0"), ("OLLAMA_MAX_LOADED_MODELS", "1"))


def user_env(name):
    """The variable as a new process would see it (Windows user environment), else the current one."""
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                return str(winreg.QueryValueEx(key, name)[0])
        except OSError:
            pass
    return os.environ.get(name, "")


def wsl_capped():
    config_file = Path.home() / ".wslconfig"
    return sys.platform != "win32" or (config_file.is_file() and "memory=" in config_file.read_text(encoding="utf-8", errors="replace").replace(" ", ""))


def doctor():
    vram, models = vram_mb(), ollama_models()
    disk = shutil.disk_usage(ROOT).free // 2**30
    wanted = {config.MASTER_MODEL, config.PROJECT_CODER_MODEL}
    with socket.socket() as probe:
        port_busy = probe.connect_ex(("127.0.0.1", 8000)) == 0
    checks = [
        ("Ollama çalışıyor", models is not None, "Ollama uygulamasını başlat"),
        ("Gerekli modeller kurulu", models is not None and wanted <= set(models), " ; ".join(f"ollama pull {m}" for m in sorted(wanted - set(models or [])))),
        ("Docker çalışıyor", bool(_out(["docker", "info", "--format", "{{.ServerVersion}}"])), "Docker Desktop'ı başlat (kod testleri için)"),
        ("Görsel denetim tarayıcısı", bool(visual_audit.browser_path()), "Microsoft Edge ya da Chrome kur"),
        ("Boş disk en az 10 GB", disk >= 10, f"{disk} GB boş; yer aç"),
        *((f"{name}={value}", user_env(name) == value, f"[Environment]::SetEnvironmentVariable('{name}','{value}','User') ve Ollama'yı yeniden başlat")
          for name, value in OLLAMA_SETTINGS),
        ("WSL2 bellek sınırı (.wslconfig)", wsl_capped(), "%UserProfile%\\.wslconfig içine [wsl2] memory=10GB yaz (32 GB RAM için)"),
    ]
    print(f"VRAM: {vram} MB | RAM: {psutil.virtual_memory().total // 2**30} GB | CPU: {psutil.cpu_count()} | disk boş: {disk} GB")
    print(f"Profil: {profile_for(vram)} | port 8000: {'dolu' if port_busy else 'boş'}")
    for name, ok, fix in checks:
        print(("[TAMAM] " if ok else "[EKSİK] ") + name + ("" if ok else f" -> {fix}"))
    return sum(not ok for _n, ok, _f in checks)


def unload():
    """Ask Ollama to drop every loaded model so another GPU job can run."""
    try:
        loaded = [m["name"] for m in httpx.get(f"{config.OLLAMA_URL}/api/ps", timeout=5).json().get("models", [])]
        for name in loaded:
            httpx.post(f"{config.OLLAMA_URL}/api/generate", json={"model": name, "keep_alive": 0}, timeout=30)  # model unload only, no inference
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        print(f"Ollama'ya ulaşılamadı: {exc}")
        return 1
    print("Bellekten çıkarılan: " + (json.dumps(loaded) if loaded else "yüklü model yoktu"))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="ai-os")
    parser.add_argument("command", choices=["doctor", "up", "unload", "bench", "export-training", "import-gguf"])
    parser.add_argument("path", nargs="?", help="export-training: output folder; import-gguf: model file")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--lan", action="store_true", help="listen on all interfaces (teammates can reach it)")
    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "unload":
        return unload()
    if args.command == "export-training":
        counts = training_pack.export(Path(args.path or "training-pack"))
        print(f"Dışa aktarıldı: {counts['sft']} doğrulanmış örnek, {counts['dpo']} tercih çifti")
        return 0
    if args.command == "import-gguf":
        try:
            body = training_pack.modelfile(Path(args.path or ""))
        except ValueError as exc:
            print(exc)
            return 1
        target = ROOT / "Modelfile.platform-coder"
        target.write_text(body, encoding="utf-8")
        return subprocess.call(["ollama", "create", "platform-coder", "-f", str(target)])
    if args.command == "bench":
        return subprocess.call([sys.executable, str(ROOT / "scripts" / "e2e_stress.py"), "web", "image"])
    python = ROOT / "master" / "venv" / "Scripts" / "python.exe"
    return subprocess.call([str(python if python.is_file() else sys.executable), "-m", "uvicorn", "app:app", "--app-dir", str(ROOT / "master"),
                            "--host", "0.0.0.0" if args.lan else "127.0.0.1", "--port", str(args.port)])


if __name__ == "__main__":
    sys.exit(main())
