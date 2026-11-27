"""Fill the local vendor vault: fonts, icons, chart/diagram/maths libraries, the accessibility checker and offline docs.

Usage: python scripts/vendor_fetch.py [--docs-only | --libs-only]
Libraries come from the npm registry and are accepted only when the tarball matches the registry's SHA-512; only the
listed files are copied out (no install script ever runs). Docs come from documents.devdocs.io. Everything lands in
master/data/vendor (not in git) with a lock file of versions and SHA-256 digests.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "master" / "data" / "vendor"
AGENT = {"User-Agent": "vendor-fetch"}

LIBRARIES = {
    "@fontsource/inter": ("5.3.0", ["files/inter-latin-[4-7]00-normal.woff2", "files/inter-latin-ext-[4-7]00-normal.woff2", "LICENSE"]),
    "@fontsource/jetbrains-mono": ("5.3.0", ["files/jetbrains-mono-latin-[47]00-normal.woff2", "files/jetbrains-mono-latin-ext-[47]00-normal.woff2", "LICENSE"]),
    "lucide-static": ("1.82.0", ["sprite.svg", "LICENSE"]),
    "chart.js": ("4.6.2", ["dist/chart.umd.js", "dist/chart.umd.min.js", "LICENSE.md"]),
    "mermaid": ("12.3.0", ["dist/mermaid.min.js", "LICENSE"]),
    "katex": ("0.19.1", ["dist/katex.min.js", "dist/katex.min.css", "dist/fonts/*.woff2", "LICENSE"]),
    "axe-core": ("4.14.1", ["axe.min.js", "LICENSE"]),
    "cytoscape": ("3.35.0", ["dist/cytoscape.min.js", "LICENSE"]),
    "vega": ("6.4.0", ["build/vega.min.js", "LICENSE"]),
    "vega-lite": ("6.5.0", ["build/vega-lite.min.js", "LICENSE"]),
    "vega-embed": ("7.4.0", ["build/vega-embed.min.js", "LICENSE"]),
    "plotly.js-basic-dist-min": ("4.3.0", ["plotly-basic.min.js", "LICENSE"]),
}
# Programs from the project's own release page, accepted only with the pinned SHA-256: name -> (url, digest, member to extract)
PROGRAMS = {
    "d2": ("https://github.com/d2lang/d2/releases/download/v0.9.0/d2-v0.9.0-windows-amd64.tar.gz",
           "5f63b643de8f5a6dfb922d172e1b5496e4caf47497c33c4427cf1127f28c340f", "d2-v0.9.0/bin/d2.exe"),
}
DOCS = ("html", "css", "javascript", "dom", "python~3.12", "fastapi", "sqlite", "playwright")


def fetch(url: str, limit: int = 120_000_000) -> bytes:
    if not url.startswith("https://"):
        raise ValueError(f"yalnız https: {url}")
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=300) as resp:  # noqa: S310 - https checked above
        data = resp.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"beklenenden büyük: {url}")
    return data


def library(name: str, version: str, wanted: list[str]) -> dict:
    meta = json.loads(fetch(f"https://registry.npmjs.org/{name}/{version}"))
    algorithm, expected = meta["dist"]["integrity"].split("-", 1)
    tarball = fetch(meta["dist"]["tarball"])
    if algorithm != "sha512" or base64.b64encode(hashlib.sha512(tarball).digest()).decode() != expected:
        raise ValueError(f"{name}: bütünlük özeti uyuşmuyor")
    target = VAULT / "lib" / name.replace("@", "").replace("/", "-")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        for member in archive:
            relative = member.name.split("/", 1)[-1]
            if not member.isfile() or ".." in relative.split("/") or not any(fnmatch.fnmatch(relative, pattern) for pattern in wanted):
                continue
            content = archive.extractfile(member).read()
            out = target / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(content)
            files[out.relative_to(VAULT).as_posix()] = hashlib.sha256(content).hexdigest()
    if not files:
        raise ValueError(f"{name}: istenen dosya bulunamadı")
    return {"version": version, "license": meta.get("license"), "files": files}


def program(name: str) -> dict:
    url, digest, member = PROGRAMS[name]
    archive_bytes = fetch(url)
    if hashlib.sha256(archive_bytes).hexdigest() != digest:
        raise ValueError(f"{name}: indirilen dosyanın özeti beklenenle uyuşmuyor")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        content = archive.extractfile(member).read()  # one named member; nothing else is written
    target = VAULT / "bin" / Path(member).name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {"url": url, "sha256": digest, "files": {target.relative_to(VAULT).as_posix(): hashlib.sha256(content).hexdigest()}}


def docs(slug: str) -> dict:
    folder = VAULT / "docs" / slug
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ("index.json", "db.json"):
        data = fetch(f"https://documents.devdocs.io/{slug}/{name}")
        json.loads(data)  # a web page instead of the data would fail here
        (folder / name).write_bytes(data)
        files[(folder / name).relative_to(VAULT).as_posix()] = hashlib.sha256(data).hexdigest()
    return {"files": files, "bytes": sum((folder / n).stat().st_size for n in ("index.json", "db.json"))}


def main() -> int:
    lock_path = VAULT / "vendor.lock.json"
    VAULT.mkdir(parents=True, exist_ok=True)
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        lock = {"libraries": {}, "docs": {}}
    failed = []
    jobs = []
    if "--docs-only" not in sys.argv:
        jobs += [("libraries", n, lambda n=n, v=v, w=w: library(n, v, w)) for n, (v, w) in LIBRARIES.items()]
    if "--docs-only" not in sys.argv and sys.platform == "win32":
        lock.setdefault("programs", {})
        jobs += [("programs", n, lambda n=n: program(n)) for n in PROGRAMS]
    if "--libs-only" not in sys.argv:
        jobs += [("docs", s, lambda s=s: docs(s)) for s in DOCS]
    for kind, name, job in jobs:
        try:
            lock[kind][name] = job()
            print(f"tamam  {name}: {len(lock[kind][name]['files'])} dosya", flush=True)
        except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
            failed.append(name)
            print(f"HATA   {name}: {exc}", flush=True)
        lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(p.stat().st_size for p in VAULT.rglob("*") if p.is_file())
    print(f"kasa: {VAULT} ({total / 2**20:.0f} MB), başarısız: {failed or 'yok'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
