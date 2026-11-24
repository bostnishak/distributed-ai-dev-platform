"""Minimal client for POST /api/assistant/chat/stream (multipart) that returns text, events and timing."""

import json
import time
import uuid
import urllib.request

BASE = "http://127.0.0.1:8099"


def chat(prompt, history=None, file=None, timeout=240):
    boundary = uuid.uuid4().hex
    parts = []

    def field(name, value):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    field("prompt", prompt)
    field("history", json.dumps(history or []))
    field("user_id", "audit")
    field("conversation_id", uuid.uuid4().hex[:8])
    if file:
        name, data = file
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(
        BASE + "/api/assistant/chat/stream", data=b"".join(parts), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    started = time.time()
    text, events, meta, error = [], [], {}, None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except ValueError:
                    continue
                events.append(event)
                kind = event.get("type")
                if kind == "token":
                    text.append(event.get("content") or event.get("token") or event.get("text") or "")
                elif kind == "done":
                    meta = event
                elif kind == "error":
                    error = event.get("message") or str(event)
    except Exception as exc:
        error = repr(exc)
    return {"text": "".join(text), "events": events, "meta": meta, "error": error, "seconds": round(time.time() - started, 1)}


if __name__ == "__main__":
    import sys

    result = chat(sys.argv[1])
    print(result["seconds"], "s", "error:", result["error"])
    print([e.get("type") for e in result["events"]][:12], "...")
    print(json.dumps(result["meta"], ensure_ascii=False)[:600])
    print(result["text"][:600])
