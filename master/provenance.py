"""Signed record of how a project was produced: request and file hashes, test verdict, dependency list (CycloneDX).

The Ed25519 key is created on first use in the data directory; `verify` shows whether files changed after delivery.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

import config

FILE_NAME = ".provenance.json"
_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(?:[=<>!~]=?\s*([0-9][\w.]*))?")


def _key() -> Ed25519PrivateKey:
    path = Path(config.DB_PATH).resolve().parent / ".provenance_key"
    if path.is_file():
        return Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
    return key


def _hashes(ws_dir: Path) -> dict[str, str]:
    files = sorted(p for p in ws_dir.rglob("*") if p.is_file() and not any(part.startswith(".") for part in p.relative_to(ws_dir).parts))
    return {p.relative_to(ws_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def sbom(ws_dir: Path) -> dict[str, Any]:
    """CycloneDX list of the declared Python and Node dependencies."""
    parts: list[dict[str, str]] = []
    req = ws_dir / "requirements.txt"
    for line in req.read_text(encoding="utf-8", errors="replace").splitlines() if req.is_file() else []:
        if not line.lstrip().startswith(("#", "-")) and (m := _REQ_RE.match(line)):
            parts.append({"type": "library", "name": m.group(1), "version": m.group(2) or "", "purl": f"pkg:pypi/{m.group(1).lower()}"})
    pkg = ws_dir / "package.json"
    if pkg.is_file():
        try:
            declared = json.loads(pkg.read_text(encoding="utf-8")).get("dependencies") or {}
        except (json.JSONDecodeError, AttributeError):
            declared = {}
        parts += [{"type": "library", "name": n, "version": str(v), "purl": f"pkg:npm/{n}"} for n, v in declared.items()]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "components": parts}


def write(ws_dir: Path, request: str, warnings: list[str]) -> None:
    body = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "request_sha256": hashlib.sha256(request.encode()).hexdigest(),
            "files": _hashes(ws_dir), "warnings": warnings, "sbom": sbom(ws_dir)}
    key = _key()
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    (ws_dir / FILE_NAME).write_text(json.dumps({**body, "public_key": public.hex(), "signature": key.sign(payload).hex()}, ensure_ascii=False, indent=2), encoding="utf-8")


def verify(ws_dir: Path) -> dict[str, Any]:
    """{signed, changed}: whether the record is genuine for this installation and which files differ from it."""
    try:
        record = json.loads((ws_dir / FILE_NAME).read_text(encoding="utf-8"))
        signature, public = bytes.fromhex(record.pop("signature")), bytes.fromhex(record.pop("public_key"))
        if public != _key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw):
            return {"signed": False, "changed": []}
        Ed25519PublicKey.from_public_bytes(public).verify(signature, json.dumps(record, sort_keys=True, ensure_ascii=False).encode())
    except (OSError, ValueError, KeyError, InvalidSignature):
        return {"signed": False, "changed": []}
    now, then = _hashes(ws_dir), record["files"]
    return {"signed": True, "changed": sorted({n for n in set(now) | set(then) if now.get(n) != then.get(n)})}
