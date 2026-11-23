"""Counters, gauges and histograms in the Prometheus text format (OPS-02), no dependencies.

Labels are kept to a small fixed set (route templates, not raw paths) so the number of series cannot grow
with traffic. ``render()`` is what ``GET /metrics`` returns.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 120.0)
MAX_SERIES = 2000

_lock = threading.Lock()
_help: dict[str, tuple[str, str]] = {}
_counters: dict[tuple, float] = {}
_gauges: dict[tuple, float] = {}
_hist: dict[tuple, list[float]] = {}  # (name, labels) -> bucket counts..., sum, count
STARTED = time.time()


def _key(name: str, labels: dict) -> tuple:
    return (name, tuple(sorted((str(k), str(v)) for k, v in labels.items())))


def describe(name: str, kind: str, text: str) -> None:
    _help[name] = (kind, text)


def _room() -> bool:
    return len(_counters) + len(_gauges) + len(_hist) < MAX_SERIES


def inc(name: str, value: float = 1.0, **labels) -> None:
    key = _key(name, labels)
    with _lock:
        if key in _counters or _room():
            _counters[key] = _counters.get(key, 0.0) + value


def gauge(name: str, value: float, **labels) -> None:
    key = _key(name, labels)
    with _lock:
        if key in _gauges or _room():
            _gauges[key] = float(value)


def observe(name: str, value: float, **labels) -> None:
    key = _key(name, labels)
    with _lock:
        if key not in _hist:
            if not _room():
                return
            _hist[key] = [0.0] * (len(BUCKETS) + 2)
        row = _hist[key]
        for i, bound in enumerate(BUCKETS):
            if value <= bound:
                row[i] += 1
        row[-2] += value
        row[-1] += 1


@contextmanager
def timer(name: str, **labels):
    start = time.perf_counter()
    try:
        yield
    finally:
        observe(name, time.perf_counter() - start, **labels)


def reset() -> None:
    with _lock:
        _counters.clear()
        _gauges.clear()
        _hist.clear()


def _fmt(labels: tuple, extra: tuple = ()) -> str:
    items = [*labels, *extra]
    if not items:
        return ""
    inner = ",".join(f'{k}="{v.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"' for k, v in items)
    return "{" + inner + "}"


def render() -> str:
    with _lock:
        counters, gauges, hist = dict(_counters), dict(_gauges), {k: list(v) for k, v in _hist.items()}
    gauges[_key("process_uptime_seconds", {})] = time.time() - STARTED
    lines: list[str] = []
    for name in sorted({k[0] for k in counters}):
        _kind, text = _help.get(name, ("counter", name))
        lines += [f"# HELP {name} {text}", f"# TYPE {name} counter"]
        lines += [f"{n}{_fmt(lb)} {v:g}" for (n, lb), v in sorted(counters.items()) if n == name]
    for name in sorted({k[0] for k in gauges}):
        _kind, text = _help.get(name, ("gauge", name))
        lines += [f"# HELP {name} {text}", f"# TYPE {name} gauge"]
        lines += [f"{n}{_fmt(lb)} {v:g}" for (n, lb), v in sorted(gauges.items()) if n == name]
    for name in sorted({k[0] for k in hist}):
        _kind, text = _help.get(name, ("histogram", name))
        lines += [f"# HELP {name} {text}", f"# TYPE {name} histogram"]
        for (n, lb), row in sorted(hist.items()):
            if n != name:
                continue
            for bound, count in zip(BUCKETS, row[:-2], strict=True):
                lines.append(f"{n}_bucket{_fmt(lb, (('le', str(bound)),))} {count:g}")
            lines.append(f"{n}_bucket{_fmt(lb, (('le', '+Inf'),))} {row[-1]:g}")
            lines.append(f"{n}_sum{_fmt(lb)} {row[-2]:g}")
            lines.append(f"{n}_count{_fmt(lb)} {row[-1]:g}")
    return "\n".join(lines) + "\n"


describe("http_requests_total", "counter", "HTTP requests by method, route template and status")
describe("http_request_duration_seconds", "histogram", "HTTP request duration in seconds by route template")
describe("http_requests_rejected_total", "counter", "Requests refused before reaching a route (too large)")
describe("errors_total", "counter", "Unhandled exceptions by kind")
describe("process_uptime_seconds", "gauge", "Seconds since the process started")
