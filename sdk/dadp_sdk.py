"""ENT-05: Lightweight Zero-Dependency Python SDK for the Distributed AI Development Platform."""

from __future__ import annotations

import json
import urllib.request
from typing import Any


class DadpClient:
    """Synchronous HTTP client for DADP Master REST APIs (health, chat, RAG, tools, OpenAI-compatible)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", admin_token: str = "", timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        if self.admin_token:
            headers["X-Admin-Token"] = self.admin_token
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def ready(self) -> dict[str, Any]:
        return self._request("GET", "/ready")

    def list_models(self) -> dict[str, Any]:
        return self._request("GET", "/api/gateway/models")

    def rag_search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        return self._request("POST", "/api/rag/search", {"query": query, "top_k": top_k})

    def calculate_tax(self, annual_income_try: float) -> dict[str, Any]:
        return self._request("POST", "/api/tools/domains/turkey-tax", {"annual_income_try": annual_income_try})
