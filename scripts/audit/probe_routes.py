"""Calls every API route of an isolated master and records what actually happens."""

import json
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8099"
SKIP = re.compile(r"(exec|run-code|launch|start-server|build-exe|backup|restore|erase|shutdown|/stream|/chat|/ws|download|export|docker|self-heal|/git)", re.I)


def call(method, path, body=None, timeout=15):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read(200_000)
            return resp.status, raw, time.time() - started, resp.headers
    except urllib.error.HTTPError as err:
        return err.code, err.read(200_000), time.time() - started, err.headers
    except Exception as exc:  # timeout or connection error
        return 0, repr(exc).encode(), time.time() - started, {}


spec = json.loads(call("GET", "/openapi.json")[1])
results = []
for path, methods in spec["paths"].items():
    for method, op in methods.items():
        if method.upper() not in ("GET", "POST", "PUT", "PATCH"):
            continue
        if SKIP.search(path):
            results.append({"route": f"{method.upper()} {path}", "skipped": True})
            continue
        url = re.sub(r"\{[^}]+\}", "1", path)
        params = [p for p in op.get("parameters", []) if p.get("in") == "query" and p.get("required")]
        if params:
            url += "?" + "&".join(f"{p['name']}=1" for p in params)
        content = op.get("requestBody", {}).get("content", {})
        body = {} if "application/json" in content else None
        if content and "application/json" not in content:
            results.append({"route": f"{method.upper()} {path}", "skipped": True, "why": "multipart"})
            continue
        status, raw, took, headers = call(method.upper(), url, body)
        text = raw.decode("utf-8", "replace")
        flags = []
        if status >= 500:
            flags.append("5xx")
        if status == 0:
            flags.append("no-response")
        if took > 3:
            flags.append("slow")
        if re.search(r"Traceback|File \"|C:\\\\Users|C:/Users", text):
            flags.append("leaks-internals")
        if 200 <= status < 300 and body == {} and method.upper() in ("POST", "PUT", "PATCH"):
            flags.append("accepts-empty-body")
        if status == 200 and re.search(r'"(error|traceback)"\s*:', text[:2000], re.I):
            flags.append("200-with-error")
        if status < 500 and status and not str(headers.get("content-type", "")).startswith("application/json") and "html" not in str(headers.get("content-type", "")) and text:
            flags.append("non-json")
        if not op.get("responses", {}).get("200", {}).get("content") and status == 200:
            flags.append("no-response-schema")
        if not op.get("summary") and not op.get("description"):
            flags.append("undocumented")
        results.append({"route": f"{method.upper()} {path}", "status": status, "ms": round(took * 1000), "flags": flags, "snippet": text[:160]})

out = sys.argv[1]
open(out, "w", encoding="utf-8").write(json.dumps(results, ensure_ascii=False, indent=1))
probed = [r for r in results if not r.get("skipped")]
print("routes", len(results), "probed", len(probed), "skipped", len(results) - len(probed))
from collections import Counter

print(Counter(f for r in probed for f in r["flags"]))
print(Counter(r["status"] for r in probed))
