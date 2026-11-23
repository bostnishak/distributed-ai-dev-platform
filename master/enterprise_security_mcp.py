"""Enterprise Security (RBAC & Token Signing), AS9100 Immutable SHA-256 Audit Trail, and Local MCP Registry.

Implements Cluster D modules [M55] and [M56]:
- RBACManager: 6 enterprise roles (admin, lead_engineer, developer, cam_programmer, quality_inspector, operator),
  PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 token signing/verification, and permission enforcement.
- AuditTrail: AS9100 tamper-evident SHA-256 hash-chained JSONL audit log in config.DATA_DIR / "audit_chain.jsonl".
- MCPRegistry: Local Model Context Protocol (MCP) JSON-schema tool registry and deterministic execution engine.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "system:admin",
        "users:manage",
        "audit:read",
        " audit:verify",
        "audit:verify",
        "cad:analyze",
        "cam:generate",
        "cmm:offset",
        "erp:schedule",
        "code:build",
        "code:execute",
        "mcp:invoke",
    },
    "lead_engineer": {
        "audit:read",
        "audit:verify",
        "cad:analyze",
        "cam:generate",
        "cmm:offset",
        "erp:schedule",
        "code:build",
        "code:execute",
        "mcp:invoke",
    },
    "developer": {
        "code:build",
        "code:execute",
        "cad:analyze",
        "mcp:invoke",
    },
    "cam_programmer": {
        "cad:analyze",
        "cam:generate",
        "cmm:offset",
        "erp:schedule",
        "mcp:invoke",
    },
    "quality_inspector": {
        "cad:analyze",
        "cmm:offset",
        "audit:read",
        "audit:verify",
    },
    "operator": {
        "cam:read",
        "cmm:read",
        "erp:read",
    },
}


class RBACManager:
    """Enterprise 6-tier Role-Based Access Control with PBKDF2-HMAC-SHA256 and HMAC-SHA256 tokens."""

    ROLES: tuple[str, ...] = (
        "admin",
        "lead_engineer",
        "developer",
        "cam_programmer",
        "quality_inspector",
        "operator",
    )

    def __init__(self, secret_key: str | None = None, iterations: int = 120_000) -> None:
        raw_secret = secret_key or config.AGENT_TOKEN or "cm6453-enterprise-local-hmac-secret-key"
        self._secret = raw_secret.encode("utf-8")
        self._iterations = max(int(iterations), 10_000)
        self._users: dict[str, dict[str, Any]] = {}

    def hash_password(self, password: str, salt: bytes | None = None) -> str:
        """Hash a plaintext password using PBKDF2-HMAC-SHA256."""
        if not password:
            raise ValueError("Password cannot be empty")
        salt_bytes = salt if salt is not None else secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, self._iterations)
        return f"pbkdf2_sha256${self._iterations}${salt_bytes.hex()}${dk.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Constant-time verification of a password against its PBKDF2-HMAC-SHA256 hash."""
        try:
            algo, iter_str, salt_hex, hash_hex = password_hash.split("$")
            if algo != "pbkdf2_sha256":
                return False
            iters = int(iter_str)
            salt_bytes = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iters)
            return hmac.compare_digest(candidate, expected)
        except Exception:
            return False

    def register_user(self, username: str, password: str, role: str) -> dict[str, Any]:
        """Register a user with one of the 6 enterprise roles."""
        uname = username.strip()
        r_norm = role.strip().lower()
        if r_norm not in ROLE_PERMISSIONS:
            raise ValueError(f"Unsupported role '{role}'. Allowed roles: {list(ROLE_PERMISSIONS)}")
        pw_hash = self.hash_password(password)
        record = {
            "username": uname,
            "role": r_norm,
            "password_hash": pw_hash,
            "permissions": sorted(ROLE_PERMISSIONS[r_norm]),
        }
        self._users[uname] = record
        return {"username": uname, "role": r_norm, "permissions": record["permissions"]}

    def sign_token(self, username: str, role: str, ttl_seconds: int = 3600) -> str:
        """Issue an HMAC-SHA256 signed token containing username, role, and expiration."""
        r_norm = role.strip().lower()
        if r_norm not in ROLE_PERMISSIONS:
            raise ValueError(f"Invalid role: {role}")
        payload = {
            "sub": username.strip(),
            "role": r_norm,
            "iat": int(time.time()),
            "exp": int(time.time()) + int(ttl_seconds),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        sig = hmac.new(self._secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{sig}"

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify HMAC-SHA256 signature and expiration of a token."""
        if not token or "." not in token:
            raise ValueError("Malformed token")
        payload_b64, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(self._secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("Invalid token signature")
        padding = "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("Token has expired")
        return payload

    def authenticate(self, username: str, password: str, ttl_seconds: int = 3600) -> str:
        """Authenticate registered user and return signed token."""
        user = self._users.get(username.strip())
        if not user or not self.verify_password(password, user["password_hash"]):
            raise PermissionError("Invalid username or password")
        return self.sign_token(user["username"], user["role"], ttl_seconds=ttl_seconds)

    def has_permission(self, role_or_token: str, permission: str) -> bool:
        """Check whether a role name or signed token grants the requested permission."""
        role = role_or_token.strip().lower()
        if "." in role_or_token:
            try:
                claims = self.verify_token(role_or_token)
                role = str(claims.get("role", "")).lower()
            except ValueError:
                return False
        perms = ROLE_PERMISSIONS.get(role, set())
        if "system:admin" in perms:
            return True
        return permission in perms


class AuditTrail:
    """AS9100 & ISO 27001 immutable SHA-256 hash-chained audit log stored in audit_chain.jsonl."""

    GENESIS_HASH = "0" * 64

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = Path(log_path) if log_path is not None else (config.DATA_DIR / "audit_chain.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _compute_entry_hash(prev_hash: str, timestamp: str, actor: str, action: str, payload: dict[str, Any]) -> str:
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        payload_digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        material = f"{prev_hash}|{timestamp}|{actor}|{action}|{payload_digest}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _get_last_hash(self) -> str:
        if not self.log_path.exists():
            return self.GENESIS_HASH
        last_line = ""
        with self.log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last_line = line.strip()
        if not last_line:
            return self.GENESIS_HASH
        record = json.loads(last_line)
        return str(record.get("entry_hash", self.GENESIS_HASH))

    def append_event(self, actor: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Append a tamper-evident SHA-256 hash-chained event to audit_chain.jsonl."""
        prev_hash = self._get_last_hash()
        ts = datetime.now(UTC).isoformat()
        safe_payload = payload if isinstance(payload, dict) else {"value": payload}
        entry_hash = self._compute_entry_hash(prev_hash, ts, actor, action, safe_payload)
        entry = {
            "timestamp": ts,
            "actor": actor,
            "action": action,
            "payload": safe_payload,
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return entry

    def read_events(self) -> list[dict[str, Any]]:
        """Read all audit entries from the JSONL chain."""
        if not self.log_path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                raw = line.strip()
                if raw:
                    events.append(json.loads(raw))
        return events

    def verify_chain(self) -> bool:
        """Verify cryptographic integrity of the entire SHA-256 hash chain."""
        if not self.log_path.exists():
            return True
        expected_prev = self.GENESIS_HASH
        try:
            with self.log_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    raw = line.strip()
                    if not raw:
                        continue
                    record = json.loads(raw)
                    if record.get("prev_hash") != expected_prev:
                        return False
                    recomputed = self._compute_entry_hash(
                        prev_hash=expected_prev,
                        timestamp=str(record["timestamp"]),
                        actor=str(record["actor"]),
                        action=str(record["action"]),
                        payload=dict(record.get("payload") or {}),
                    )
                    if not hmac.compare_digest(str(record.get("entry_hash", "")), recomputed):
                        return False
                    expected_prev = recomputed
            return True
        except Exception:
            return False


class MCPRegistry:
    """Local Model Context Protocol (MCP) plug-and-play JSON-schema tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[..., Any],
    ) -> dict[str, Any]:
        """Register a local MCP tool with its JSON schema and Python handler."""
        t_name = name.strip()
        if not t_name:
            raise ValueError("Tool name cannot be empty")
        if not callable(handler):
            raise TypeError("Tool handler must be callable")
        spec = {
            "name": t_name,
            "description": description.strip(),
            "inputSchema": input_schema,
            "handler": handler,
        }
        self._tools[t_name] = spec
        return {"name": t_name, "description": spec["description"], "inputSchema": input_schema}

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP-compliant tool descriptors without internal handler references."""
        return [
            {
                "name": spec["name"],
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for spec in self._tools.values()
        ]

    def invoke_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate required schema fields and invoke a registered MCP tool."""
        if name not in self._tools:
            raise KeyError(f"MCP tool '{name}' is not registered")
        spec = self._tools[name]
        args = dict(arguments or {})
        schema = spec.get("inputSchema") or {}
        required_fields = schema.get("required") or []
        for req in required_fields:
            if req not in args:
                raise ValueError(f"Missing required argument '{req}' for MCP tool '{name}'")
        props = schema.get("properties") or {}
        type_map: dict[str, tuple[type, ...]] = {
            "string": (str,),
            "number": (int, float),
            "integer": (int,),
            "boolean": (bool,),
            "object": (dict,),
            "array": (list, tuple),
        }
        for key, val in args.items():
            prop_schema = props.get(key)
            if isinstance(prop_schema, dict) and "type" in prop_schema:
                expected_types = type_map.get(str(prop_schema["type"]))
                if expected_types and not isinstance(val, expected_types):
                    raise TypeError(
                        f"Argument '{key}' for tool '{name}' expected {prop_schema['type']}, got {type(val).__name__}"
                    )
        result = spec["handler"](**args)
        return {
            "tool": name,
            "status": "ok",
            "result": result,
        }
