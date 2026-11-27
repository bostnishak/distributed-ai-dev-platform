"""Does the interface, the API and the database tell the same story after many random actions?

For a resource with a list, a create and a delete route (read from the running server's OpenAPI description) a random
but repeatable sequence of creations and deletions is performed. After every step the list the API returns must match
what was done; at the end the rows in the database and the page the user sees must match too. Documented read routes
are also called once each: none may answer with a server error or something other than what it declares.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

_STEPS = 16


class Sequence:
    """A repeatable stream of choices: the same seed always performs the same actions, so a failure can be replayed."""

    def __init__(self, seed: int) -> None:
        self.seed, self.count = seed, 0

    def number(self, below: int) -> int:
        self.count += 1
        return int.from_bytes(hashlib.sha256(f"{self.seed}:{self.count}".encode()).digest()[:8], "big") % below


@dataclass(frozen=True)
class Resource:
    collection: str  # "/api/items"
    item: str  # "/api/items/{id}" or "" when there is no delete
    fields: dict[str, str]  # name -> JSON type of the create body


@dataclass
class Report:
    checked: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _schema(spec: dict, node: dict) -> dict:
    if ref := node.get("$ref"):
        target: Any = spec
        for part in ref.removeprefix("#/").split("/"):
            target = target.get(part, {})
        return target
    return node


def resources(spec: dict) -> list[Resource]:
    paths = spec.get("paths", {})
    found = []
    for path, operations in paths.items():
        if "{" in path or "post" not in operations or "get" not in operations:
            continue
        body = operations["post"].get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
        properties = _schema(spec, body).get("properties", {})
        if not properties:
            continue
        item = next((p for p, ops in paths.items() if p.startswith(path.rstrip("/") + "/{") and p.count("/") == path.rstrip("/").count("/") + 1 and "delete" in ops), "")
        found.append(Resource(path, item, {name: str(_schema(spec, value).get("type", "string")) for name, value in properties.items() if name != "id"}))
    return found


def _value(kind: str, marker: str, rng: Sequence) -> Any:
    if kind == "integer":
        return 1 + rng.number(500)
    if kind == "number":
        return (100 + rng.number(49900)) / 100
    if kind == "boolean":
        return rng.number(2) == 1
    return marker


def _listed(client: httpx.Client, path: str) -> list[dict]:
    data = client.get(path).raise_for_status().json()
    if isinstance(data, dict):  # {"items": [...]} style envelopes
        data = next((value for value in data.values() if isinstance(value, list)), [])
    return [row for row in data if isinstance(row, dict)]


def contract(client: httpx.Client, spec: dict) -> Report:
    """Every documented GET without parameters: no server error, and JSON when JSON is declared."""
    report = Report()
    for path, operations in spec.get("paths", {}).items():
        get = operations.get("get")
        if not get or "{" in path or any(p.get("required") for p in get.get("parameters", [])):
            continue
        response = client.get(path)
        report.checked.append(f"GET {path} -> {response.status_code}")
        declared = get.get("responses", {}).get("200", {}).get("content", {})
        if response.status_code >= 500:
            report.problems.append(f"GET {path} sunucu hatası {response.status_code}")
        elif response.status_code == 200 and "application/json" in declared and "json" not in response.headers.get("content-type", ""):
            report.problems.append(f"GET {path} JSON bildiriyor ama {response.headers.get('content-type')} döndürüyor")
    return report


def _create(client: httpx.Client, resource: Resource, rng: Sequence, state: tuple[set[Any], dict[Any, str]], report: Report) -> None:
    start, alive = state
    marker = f"Özellik {rng.number(16**8):08x} İğne"
    body = {name: _value(kind, marker, rng) for name, kind in resource.fields.items()}
    response = client.post(resource.collection, json=body)
    if response.status_code not in (200, 201):
        report.problems.append(f"oluşturma {response.status_code} döndürdü: {response.text[:120]}")
        return
    new = [row for row in _listed(client, resource.collection) if row.get("id") not in alive and row.get("id") not in start]
    if len(new) != 1:
        report.problems.append(f"bir kayıt eklendikten sonra listede {len(new)} yeni kayıt var")
        return
    alive[new[0].get("id")] = marker if marker in body.values() else ""


def _delete(client: httpx.Client, resource: Resource, rng: Sequence, state: tuple[set[Any], dict[Any, str]], report: Report) -> None:
    alive = state[1]
    victim = sorted(alive, key=str)[rng.number(len(alive))]
    response = client.delete(resource.item.split("{", 1)[0] + str(victim))
    if response.status_code >= 300:
        report.problems.append(f"silme {response.status_code} döndürdü")
        return
    alive.pop(victim)


def exercise(client: httpx.Client, resource: Resource, rows: Callable[[], dict[str, int]] | None = None, seed: int = 7) -> tuple[Report, dict[Any, str]]:
    """(report, ids that should still exist with their marker text)."""
    rng, report = Sequence(seed), Report()
    start = {row.get("id") for row in _listed(client, resource.collection)}
    before = rows() if rows else {}
    alive: dict[Any, str] = {}
    for _step in range(_STEPS):
        remove = alive and resource.item and rng.number(10) < 4
        (_delete if remove else _create)(client, resource, rng, (start, alive), report)
        shown = {row.get("id") for row in _listed(client, resource.collection)} - start
        if shown != set(alive) and not report.problems:
            report.problems.append(f"API listesi yapılanlarla uyuşmuyor: beklenen {sorted(alive, key=str)}, gelen {sorted(shown, key=str)}")
        if report.problems:
            return report, alive
    report.checked.append(f"{resource.collection}: {_STEPS} rastgele ekleme/silme, API listesi her adımda tutarlı")
    if rows and before:
        grown = sum(rows().values()) - sum(before.values())
        if grown < len(alive):
            report.problems.append(f"veritabanında {grown} yeni satır var, {len(alive)} kayıt olmalıydı")
        else:
            report.checked.append(f"veritabanı: {len(alive)} kayıt için {grown} yeni satır")
    return report, alive


def check(url: str, rows: Callable[[], dict[str, int]] | None = None, page_text: Callable[[], str] | None = None) -> Report:
    """Contract and state checks of a running server; an empty report when it describes no API."""
    with httpx.Client(base_url=url, timeout=15, follow_redirects=True) as client:
        answer = client.get("/openapi.json")
        if answer.status_code != 200:
            return Report()
        spec = answer.json()
        report = contract(client, spec)
        for resource in resources(spec)[:2]:
            result, alive = exercise(client, resource, rows)
            report.checked += result.checked
            report.problems += result.problems
            if page_text and alive and not result.problems:
                text = page_text()
                missing = [marker for marker in alive.values() if marker and marker not in text]
                if missing:
                    report.problems.append(f"API'de duran {len(missing)} kayıt sayfada görünmüyor")
                else:
                    report.checked.append("sayfa, API ile aynı kayıtları gösteriyor")
    return report
