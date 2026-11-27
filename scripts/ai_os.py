"""Local launch kernel: doctor (hardware and dependencies), up (start the core only), unload (free GPU memory), bench.

Usage: python scripts/ai_os.py doctor | setup [--pull] | up [--port 8000] [--lan] | unload | bench | export-training [dir] | import-gguf <file>
Heavy parts (Docker sandbox, headless browser) start only when a task needs them and exit with it.
"""

import argparse
import asyncio
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
import arena  # noqa: E402
import config  # noqa: E402
import feature_flags  # noqa: E402
import training_pack  # noqa: E402
import verified_tasks  # noqa: E402
import visual_audit  # noqa: E402
import workspace_docker  # noqa: E402

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


CONFIG_FILE = ROOT / "ai-os.config.json"


def setup(pull: bool = False):
    """Write the profile for this machine, create the local folders and databases, and list (or pull) missing models."""
    vram, models = vram_mb(), ollama_models()
    profile = profile_for(vram)
    wanted = {config.MASTER_MODEL, config.PROJECT_CODER_MODEL, "bge-m3:latest"}
    missing = sorted(m for m in wanted if m not in set(models or []) and m.removesuffix(":latest") not in set(models or []))
    previous = feature_flags.read(CONFIG_FILE)
    settings = {"features": previous.get("features", {}), "profiles": previous.get("profiles", {"sessiz": {"enable_self_play": False, "enable_nightly_eval": False}}), "profile": profile, "vram_mb": vram, "ram_gb": psutil.virtual_memory().total // 2**30,
                "one_model_at_a_time": profile != "WORKSTATION_48GB+", "required_models": sorted(wanted)}
    CONFIG_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    config.data_dir().mkdir(parents=True, exist_ok=True)
    (config.data_dir() / "inbox").mkdir(exist_ok=True)
    print(f"Profil {profile} -> {CONFIG_FILE}")
    if models is None:
        print("Ollama'ya ulaşılamadı; uygulamayı başlatıp tekrar çalıştır.")
        return 1
    for name in missing:
        if not pull:
            print(f"Eksik model: ollama pull {name}")
        elif subprocess.call(["ollama", "pull", name]):
            return 1
    print("Modeller tamam." if not missing else ("İndirildi." if pull else "İndirmek için: python scripts/ai_os.py setup --pull"))
    return doctor()


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


def import_model(body: str, baseline: str) -> int:
    """Create the GGUF as a candidate and give it the platform name only if it passes the shadow evaluation."""
    target = ROOT / "Modelfile.platform-coder"
    target.write_text(body, encoding="utf-8")
    if subprocess.call(["ollama", "create", "platform-coder-candidate", "-f", str(target)]):
        return 1
    if not workspace_docker.available():
        print("Kod kutusu kapalı: aday ölçülemedi, platform-coder olarak YAYINLANMADI (aday: platform-coder-candidate).")
        return 2
    scores = {m: asyncio.run(verified_tasks.score(m)) for m in (baseline, "platform-coder-candidate")}
    promote, line = arena.verdict(scores["platform-coder-candidate"], scores[baseline])
    print(f"Gölge değerlendirme: {line}")
    if not promote:
        print("KAPI KAPALI: platform-coder değiştirilmedi (aday: platform-coder-candidate).")
        return 3
    print("KAPI AÇIK: aday platform-coder olarak yayınlanıyor.")
    return subprocess.call(["ollama", "cp", "platform-coder-candidate", "platform-coder"])


def main():
    parser = argparse.ArgumentParser(prog="ai-os")
    parser.add_argument("command", choices=["doctor", "setup", "up", "unload", "bench", "export-training", "import-gguf"])
    parser.add_argument("path", nargs="?", help="export-training: output folder; import-gguf: model file")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--profile", default="", help="up: ai-os.config.json içindeki özellik profili")
    parser.add_argument("--baseline", default="qwen2.5-coder:7b", help="import-gguf: model the candidate must not be worse than")
    parser.add_argument("--pull", action="store_true", help="setup: download missing models")
    parser.add_argument("--lan", action="store_true", help="listen on all interfaces (teammates can reach it)")
    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "setup":
        return setup(args.pull)
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
        return import_model(body, args.baseline)
    if args.command == "bench":
        return subprocess.call([sys.executable, str(ROOT / "scripts" / "e2e_stress.py"), "web", "image"])
    python = ROOT / "master" / "venv" / "Scripts" / "python.exe"
    if args.profile:
        try:
            feature_flags.chosen(args.profile)
        except ValueError as exc:
            print(exc)
            return 1
        os.environ["AI_OS_PROFILE"] = args.profile  # the server reads it when it loads its configuration
    return subprocess.call([str(python if python.is_file() else sys.executable), "-m", "uvicorn", "app:app", "--app-dir", str(ROOT / "master"),
                            "--host", "0.0.0.0" if args.lan else "127.0.0.1", "--port", str(args.port)])


if __name__ == "__main__":
    sys.exit(main())
