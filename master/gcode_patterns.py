"""Hole positions for G-code jobs: corners, bolt circle, grid, line, explicit points; ordered to keep rapid travel short."""

from __future__ import annotations

import math
from typing import Any

Point = tuple[float, float]


def _num(v: Any, default: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else default


def _corners(op: dict[str, Any], stock: tuple[float, float, float]) -> list[Point]:
    i = _num(op.get("inset")) or 8.0
    return [(i, i), (stock[0] - i, i), (stock[0] - i, stock[1] - i), (i, stock[1] - i)]


def _circle(op: dict[str, Any], stock: tuple[float, float, float]) -> list[Point]:
    """Bolt circle: `count` holes on a circle of diameter `pcd` around (cx, cy) (default: stock centre), first hole at `start` degrees."""
    cx, cy = _num(op.get("cx"), stock[0] / 2) or stock[0] / 2, _num(op.get("cy"), stock[1] / 2) or stock[1] / 2
    count, r, start = max(1, int(_num(op.get("count"), 4))), _num(op.get("pcd")) / 2, _num(op.get("start_angle"))
    return [(cx + r * math.cos(math.radians(start + 360.0 * k / count)), cy + r * math.sin(math.radians(start + 360.0 * k / count))) for k in range(count)]


def _grid(op: dict[str, Any], stock: tuple[float, float, float]) -> list[Point]:
    """nx x ny holes with pitch_x / pitch_y; the pattern is centred in the stock unless x0/y0 give the first hole."""
    nx, ny = max(1, int(_num(op.get("nx"), 1))), max(1, int(_num(op.get("ny"), 1)))
    px, py = _num(op.get("pitch_x")), _num(op.get("pitch_y"))
    x0 = _num(op.get("x0"), (stock[0] - (nx - 1) * px) / 2) if op.get("x0") is not None else (stock[0] - (nx - 1) * px) / 2
    y0 = _num(op.get("y0"), (stock[1] - (ny - 1) * py) / 2) if op.get("y0") is not None else (stock[1] - (ny - 1) * py) / 2
    return [(x0 + i * px, y0 + j * py) for j in range(ny) for i in range(nx)]


def _line(op: dict[str, Any], stock: tuple[float, float, float]) -> list[Point]:
    count = max(1, int(_num(op.get("count"), 2)))
    x0, y0 = _num(op.get("x0"), stock[0] / 2), _num(op.get("y0"), stock[1] / 2)
    dx, dy = _num(op.get("dx")), _num(op.get("dy"))
    return [(x0 + k * dx, y0 + k * dy) for k in range(count)]


_BUILDERS = {"corners": _corners, "circle": _circle, "grid": _grid, "line": _line}


def order_points(points: list[Point]) -> list[Point]:
    """Nearest-neighbour ordering starting from the point closest to the origin (short rapids, no jumping around)."""
    left, out = list(points), []
    cur: Point = (0.0, 0.0)
    while left:
        nxt = min(left, key=lambda p: math.dist(cur, p))
        left.remove(nxt)
        out.append(nxt)
        cur = nxt
    return out


def hole_points(op: dict[str, Any], stock: tuple[float, float, float]) -> list[Point]:
    pattern = str(op.get("pattern") or "")
    if pattern == "center":
        pts = [(stock[0] / 2, stock[1] / 2)]
    elif pattern in _BUILDERS:
        pts = _BUILDERS[pattern](op, stock)
    else:
        pts = [(float(x), float(y)) for x, y in op.get("points", [])]
    return order_points([(round(x, 4), round(y, 4)) for x, y in pts])


def missing_for(op: dict[str, Any]) -> str:
    """Question for the user when a hole pattern lacks a number that cannot be guessed; '' when complete."""
    pattern = str(op.get("pattern") or "")
    if pattern == "circle" and not _num(op.get("pcd")):
        return "Delik dairesinin çapını (PCD, mm) ve delik sayısını belirtir misin?"
    if pattern == "grid" and not (_num(op.get("pitch_x")) or _num(op.get("pitch_y"))):
        return "Izgara deliklerinin aralığını (mm) ve sütun x satır sayısını belirtir misin?"
    if pattern == "line" and not (_num(op.get("dx")) or _num(op.get("dy"))):
        return "Sıralı deliklerin aralığını (mm) ve sayısını belirtir misin?"
    if not pattern and not op.get("points"):
        return "Deliklerin konumunu (koordinat, köşe, daire ya da ızgara) belirtir misin?"
    return ""
