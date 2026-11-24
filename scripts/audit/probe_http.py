"""HTTP-level probes against an isolated master (default port 8099): headers, CORS, schemas, limits, malformed input."""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8099"
findings = []


def req(method, path, body=None, headers=None, raw=None, timeout=10):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read(5_000_000)
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read(5_000_000)
    except Exception as exc:
        return 0, {}, repr(exc).encode()


def add(rule, where, text):
    findings.append({"rule": rule, "where": where, "text": text})


# 1. security headers on the HTML shell and on an API route
status, headers, _ = req("GET", "/")
lower = {k.lower(): v for k, v in headers.items()}
for name in ("content-security-policy", "strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy", "cross-origin-opener-policy", "cross-origin-resource-policy"):
    if name not in lower:
        add("header-missing", "GET /", f"{name} yok")
csp = lower.get("content-security-policy", "")
if "unsafe-inline" in csp:
    add("csp-unsafe-inline", "GET /", csp[:140])
status, headers, _ = req("GET", "/api/agents")
lower = {k.lower(): v for k, v in headers.items()}
if "cache-control" not in lower:
    add("api-no-cache-control", "GET /api/agents", "Cache-Control başlığı yok")

# 2. CORS: foreign origin must not be echoed
status, headers, _ = req("GET", "/api/agents", headers={"Origin": "http://evil.example"})
lower = {k.lower(): v for k, v in headers.items()}
if lower.get("access-control-allow-origin") in ("*", "http://evil.example"):
    add("cors-foreign-origin-allowed", "GET /api/agents", lower["access-control-allow-origin"])
status, _, _ = req("POST", "/api/user/profiles", {"user_id": "x"}, headers={"Origin": "http://evil.example"})
if status < 400:
    add("csrf-foreign-origin-mutation-accepted", "POST /api/user/profiles", f"HTTP {status}")

# 3. malformed JSON must be 4xx, never 5xx
for path in ("/api/rag/search", "/api/hallucination/verify", "/api/orchestrator/run", "/api/studios/research", "/api/games/build", "/api/factory/plan", "/api/domains/finance/dcf"):
    status, _, body = req("POST", path, raw=b"{not json")
    if status >= 500 or status == 0:
        add("malformed-json-5xx", f"POST {path}", f"HTTP {status}")
    status, _, body = req("POST", path, raw=b'{"a": ' + b"[" * 5000 + b"]" * 5000 + b"}")
    if status >= 500 or status == 0:
        add("deeply-nested-json-5xx", f"POST {path}", f"HTTP {status}")

# 4. no rate limit on cheap GET
started = time.time()
codes = [req("GET", "/api/agents")[0] for _ in range(120)]
if 429 not in codes:
    add("no-rate-limit", "GET /api/agents", f"120 istek {time.time() - started:.1f} sn içinde, hiçbiri 429 değil")

# 5. oversized body
status, _, _ = req("POST", "/api/rag/ingest", raw=b'{"text": "' + b"a" * (70 * 1024 * 1024) + b'"}', timeout=60)
if status not in (413, 422, 400, 0):
    add("oversized-body-not-rejected", "POST /api/rag/ingest", f"70 MB gövde için HTTP {status}")

# 6. path traversal on file-serving routes
for path in ("/api/assistant/media/..%2f..%2fplatform.db", "/api/studio/workspaces/1/file?path=../../platform.db", "/api/studios/media/..%5c..%5cplatform.db"):
    status, _, body = req("GET", path)
    if status == 200 and len(body) > 0:
        add("path-traversal-served", path, f"HTTP 200, {len(body)} bayt")

# 7. response schema coverage from OpenAPI
spec = json.loads(req("GET", "/openapi.json")[2])
for path, methods in spec["paths"].items():
    for method, op in methods.items():
        if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            continue
        ok = op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema")
        if ok in (None, {}):
            add("route-without-response-schema", f"{method.upper()} {path}", "200 yanıtı için şema yok (sözleşme testi yazılamaz)")
        if not (op.get("description") or "").strip():
            add("route-without-description", f"{method.upper()} {path}", "açıklama/docstring yok")

# 8. cookie flags on login
status, headers, _ = req("POST", "/api/auth/setup", {"username": "audit", "password": "correct-horse-battery-9"})
cookie = headers.get("set-cookie", "") or headers.get("Set-Cookie", "")
if cookie:
    for flag in ("HttpOnly", "SameSite"):
        if flag.lower() not in cookie.lower():
            add("cookie-flag-missing", "POST /api/auth/setup", flag)

out = sys.argv[1]
open(out, "w", encoding="utf-8").write(json.dumps(findings, ensure_ascii=False, indent=1))
import collections

print(len(findings), collections.Counter(f["rule"] for f in findings).most_common())
