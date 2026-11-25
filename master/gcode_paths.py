"""Milling and drilling toolpaths (3-axis) written as G-code lines.

Conventions: X0 Y0 = stock lower-left corner, Z0 = stock top, millimetres. Inside cuts (pockets, bores) run clockwise and outside
contours counter-clockwise, which is climb milling with a clockwise spindle. Every cut descends in equal layers; pockets and bores
enter with a helix instead of plunging, contours and slots ramp in, and walls are finished in a separate full-depth pass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

SAFE_Z, CLEAR_Z, RETRACT_R = 5.0, 25.0, 2.0
ALLOW = 0.2  # material left on walls by the roughing passes
Point = tuple[float, float]


def fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") if abs(x) > 1e-9 else "0"


class Writer:
    """Numbered G-code lines; remembers the last XY so zero-length moves are never written."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.n = 10
        self.xy: Point | None = None
        self.feed: int | None = None  # modal feed: F is only written when it changes

    def add(self, text: str) -> None:
        if text.startswith("(") or text.startswith("%") or text.startswith("O"):
            self.lines.append(text)
            return
        self.lines.append(f"N{self.n} {text}")
        self.n += 10

    def move(self, code: str, x: float | None = None, y: float | None = None, z: float | None = None, f: float | None = None, ij: Point | None = None) -> None:  # noqa: PLR0913
        """One motion block; G0/G1 moves that would not change anything are dropped."""
        if code in ("G0", "G1") and z is None and x is not None and y is not None and self.xy is not None and math.dist(self.xy, (x, y)) < 1e-6:
            return
        words = [code]
        words += [f"X{fmt(x)}"] if x is not None else []
        words += [f"Y{fmt(y)}"] if y is not None else []
        words += [f"Z{fmt(z)}"] if z is not None else []
        words += [f"I{fmt(ij[0])}", f"J{fmt(ij[1])}"] if ij is not None else []
        if f is not None and round(f) != self.feed:
            words.append(f"F{round(f)}")
            self.feed = round(f)
        self.add(" ".join(words))
        if x is not None and y is not None:
            self.xy = (x, y)


@dataclass
class Cut:
    """Everything a milling path needs: writer, tool diameter, depth of cut per layer, cutting feed and the stock."""

    w: Writer
    dia: float
    ap: float
    feed: int
    stock: tuple[float, float, float]
    rpm: int = 0
    mat: dict[str, Any] | None = None

    @property
    def plunge(self) -> float:
        return self.feed / 3


def layers(depth: float, ap: float) -> list[float]:
    """Equal layers down to `depth`: [-ap, -2ap, ... -depth] as negative Z values."""
    n = max(1, math.ceil(depth / max(ap, 0.05) - 1e-9))
    return [-(i + 1) * depth / n for i in range(n)]


def _start(c: Cut, x: float, y: float) -> None:
    c.w.move("G0", x, y)
    c.w.move("G0", z=SAFE_Z)
    c.w.move("G1", z=0, f=c.plunge)
    c.w.xy = (x, y)


def helix_down(c: Cut, center: Point, r: float, z_range: tuple[float, float], finish_k: float = 1.0) -> None:
    """Descend z0 -> z1 on a clockwise helix of radius r around `center` (tool must already be at center + (r, 0)); plunge when r is tiny."""
    (cx, cy), (z0, z1) = center, z_range
    if r < 0.5:
        c.w.move("G1", z=z1, f=c.plunge)
        return
    pitch = max(0.2, min(c.ap, 0.8 * r))
    z = z0
    while z > z1 + 1e-9:
        z = max(z - pitch, z1)
        c.w.move("G2", cx + r, cy, z, c.feed * 0.7, (-r, 0.0))  # inside arcs: the cutter edge travels faster than the centre, so feed is trimmed
    c.w.move("G2", cx + r, cy, None, c.feed * 0.7 * finish_k, (-r, 0.0))  # flat circle clears the floor of the entry


def face(c: Cut, depth: float) -> None:
    sx, sy, _ = c.stock
    d, step = c.dia, c.dia * 0.75
    zs = layers(depth, c.ap)
    c.w.add(f"(FACING - {fmt(depth)} mm in {len(zs)} pass(es), stepover {fmt(step)} mm)")
    rows, y = [], -d / 2 + step / 2
    while y < sy + d / 2:
        rows.append(y)
        y += step
    rows.append(sy + d / 2)
    left, right = -d / 2 - 1, sx + d / 2 + 1
    for z in zs:
        c.w.move("G0", left, rows[0])
        c.w.move("G0", z=SAFE_Z)
        c.w.move("G1", z=z, f=c.plunge)
        for k, yy in enumerate(rows):
            a, b = (left, right) if k % 2 == 0 else (right, left)
            c.w.move("G1", a, yy, None, c.feed)
            c.w.move("G1", b, yy, None, c.feed)
    c.w.move("G0", z=SAFE_Z)


def bore(c: Cut, x: float, y: float, dia: float, depth: float) -> None:
    """Hole larger than the end mill: clockwise helix down on a circle of radius (D - d) / 2, then a full finishing circle."""
    r = (dia - c.dia) / 2
    c.w.add(f"(BORE D{fmt(dia)} - helical interpolation, tool D{fmt(c.dia)}, climb milling)")
    _start(c, x + r, y)
    helix_down(c, (x, y), r, (0.0, -depth), 0.8)  # the closing flat circle at depth is the finish pass
    c.w.move("G1", x, y, None, c.feed)
    c.w.move("G0", z=SAFE_Z)


def _rings(h0: Point, step: float) -> list[Point]:
    """Rectangle half-sizes from the innermost to the outermost ring; a ring that collapses in one direction becomes a line."""
    out, k = [], 0
    while True:
        hx, hy = max(h0[0] - k * step, 0.0), max(h0[1] - k * step, 0.0)
        out.append((hx, hy))
        if hx == 0.0 and hy == 0.0:
            break
        k += 1
    return ([r for r in out if r != (0.0, 0.0)] or [(0.0, 0.0)])[::-1]


def _rect_loop(c: Cut, center: Point, half: Point, feed: float) -> None:
    (cx, cy), (hx, hy) = center, half
    for px, py in ((cx - hx, cy + hy), (cx + hx, cy + hy), (cx + hx, cy - hy), (cx - hx, cy - hy), (cx - hx, cy + hy)):
        c.w.move("G1", px, py, None, feed)


def pocket_rect(c: Cut, center: Point, size: Point, depth: float) -> None:
    """Rectangular pocket: helical entry at the centre, rings from the centre outwards (steady 40 % stepover), then a wall finishing pass."""
    d, (cx, cy), (wid, ln) = c.dia, center, size
    h0 = (max(wid / 2 - d / 2 - ALLOW, 0.0), max(ln / 2 - d / 2 - ALLOW, 0.0))
    rh = min(d * 0.35, max(h0) * 0.8)
    c.w.add(f"(POCKET {fmt(wid)}x{fmt(ln)} depth {fmt(depth)} - helical entry, rings from the centre, {fmt(ALLOW)} mm wall allowance, then finish pass)")
    zs = layers(depth, c.ap)
    for i, z in enumerate(zs):
        if i == 0:
            _start(c, cx + rh, cy)
        else:
            c.w.move("G1", cx + rh, cy, None, c.feed)
        helix_down(c, center, rh, (0.0 if i == 0 else zs[i - 1], z))
        for ring in _rings(h0, d * 0.4):
            _rect_loop(c, center, ring, c.feed)
    c.w.add("(finish walls at full depth)")
    _rect_loop(c, center, (h0[0] + ALLOW, h0[1] + ALLOW), c.feed * 0.7)
    c.w.move("G0", z=SAFE_Z)


def _circle(c: Cut, center: Point, r: float, feed: float, ccw: bool = False) -> None:
    cx, cy = center
    c.w.move("G1", cx + r, cy, None, feed)
    c.w.move("G3" if ccw else "G2", cx + r, cy, None, feed, (-r, 0.0))


def pocket_round(c: Cut, center: Point, dia: float, depth: float) -> None:
    """Circular pocket larger than the tool: helical entry, concentric circles from the centre outwards, wall finish."""
    d, (cx, cy) = c.dia, center
    r0 = max(dia / 2 - d / 2 - ALLOW, 0.0)
    rh = min(d * 0.35, r0 * 0.8)
    c.w.add(f"(ROUND POCKET D{fmt(dia)} depth {fmt(depth)} - helical entry, concentric circles, then finish pass)")
    zs = layers(depth, c.ap)
    radii = sorted({max(r0 - k * d * 0.4, 0.0) for k in range(int(r0 / (d * 0.4)) + 2)} - {0.0})
    for i, z in enumerate(zs):
        if i == 0:
            _start(c, cx + rh, cy)
        else:
            c.w.move("G1", cx + rh, cy, None, c.feed)
        helix_down(c, center, rh, (0.0 if i == 0 else zs[i - 1], z))
        for r in radii:
            _circle(c, center, r, c.feed)
    c.w.add("(finish wall at full depth)")
    _circle(c, center, r0 + ALLOW, c.feed * 0.7)
    c.w.move("G0", z=SAFE_Z)


def _obround(c: Cut, ends: tuple[Point, Point], t: float, feed: float) -> None:
    """Clockwise stadium loop (tool-centre path) around the segment p1-p2 at offset t."""
    (x1, y1), (x2, y2) = ends
    ln = math.dist(ends[0], ends[1])
    ux, uy = ((x2 - x1) / ln, (y2 - y1) / ln) if ln > 1e-9 else (1.0, 0.0)
    nx, ny = -uy, ux
    c.w.move("G1", x1 + nx * t, y1 + ny * t, None, feed)
    c.w.move("G1", x2 + nx * t, y2 + ny * t, None, feed)
    c.w.move("G2", x2 - nx * t, y2 - ny * t, None, feed, (-nx * t, -ny * t))
    c.w.move("G1", x1 - nx * t, y1 - ny * t, None, feed)
    c.w.move("G2", x1 + nx * t, y1 + ny * t, None, feed, (nx * t, ny * t))


def slot(c: Cut, ends: tuple[Point, Point], width: float, depth: float) -> None:
    """Straight slot between two centre points: ramped passes along the centre line, plus stadium loops when the slot is wider than the tool."""
    (x1, y1), (x2, y2) = ends
    d, ln = c.dia, math.dist(ends[0], ends[1])
    o = max((width - d) / 2, 0.0)
    n_loops = math.ceil(o / (0.8 * d)) if o > 0.05 else 0
    extra = f", {n_loops} wall loop(s)" if n_loops else ""
    c.w.add(f"(SLOT {fmt(width)} wide, {fmt(ln)} between centres, depth {fmt(depth)} - ramped entry{extra})")
    zs = layers(depth, c.ap)
    feed = c.feed * 0.6  # the centre pass is as wide as the tool (slotting): lower feed; the wall loops below run at the normal feed
    _start(c, x1, y1)
    for i, z in enumerate(zs):
        drop = abs(z - (zs[i - 1] if i else 0.0))
        if ln > 0 and math.degrees(math.atan2(drop, ln)) <= 8:
            c.w.move("G1", x2, y2, z, feed)
        else:
            c.w.move("G1", z=z, f=c.plunge)
            c.w.move("G1", x2, y2, None, feed)
        c.w.move("G1", x1, y1, None, feed)
    for k in range(1, n_loops + 1):
        _obround(c, ends, o * k / n_loops, c.feed * (0.7 if k == n_loops else 1.0))
    c.w.move("G0", z=SAFE_Z)


def profile_rect(c: Cut, box: tuple[float, float, float, float], depth: float) -> None:
    """Outside contour of the rectangle (x0, y0, x1, y1): counter-clockwise climb milling, ramp on the first edge, full-depth finish pass."""
    x0, y0, x1, y1 = box
    o = c.dia / 2
    zs = layers(depth, c.ap)
    c.w.add(f"(PROFILE - outside contour {fmt(x1 - x0)}x{fmt(y1 - y0)}, climb milling, {fmt(depth)} mm in {len(zs)} layer(s) + finish pass)")

    def corners(leave: float) -> tuple[float, float, float, float]:
        return x0 - o - leave, y0 - o - leave, x1 + o + leave, y1 + o + leave

    def loop(leave: float, z: float | None) -> None:
        a, b, cc, e = corners(leave)
        c.w.move("G1", a, b, None, c.feed)
        c.w.move("G1", cc, b, z, c.feed)
        for px, py in ((cc, e), (a, e), (a, b)):
            c.w.move("G1", px, py, None, c.feed)

    a0, b0, _, _ = corners(ALLOW)
    c.w.move("G0", a0 - 3, b0)
    c.w.move("G0", z=SAFE_Z)
    c.w.move("G1", z=0, f=c.plunge)
    for z in zs:
        loop(ALLOW, z)
    loop(0.0, zs[-1])
    c.w.move("G1", corners(0.0)[0] - 3, corners(0.0)[1], None, c.feed)
    c.w.move("G0", z=SAFE_Z)


def profile_circle(c: Cut, center: Point, dia: float, depth: float) -> None:
    """Outside contour of a round part: helical ramp down on a counter-clockwise circle, then a full-depth finish circle."""
    (cx, cy), d = center, c.dia
    r = dia / 2 + d / 2
    c.w.add(f"(PROFILE - round part D{fmt(dia)}, climb milling, helical ramp, finish pass)")
    c.w.move("G0", cx + r + ALLOW, cy)
    c.w.move("G0", z=SAFE_Z)
    c.w.move("G1", z=0, f=c.plunge)
    z_prev = 0.0
    for z in layers(depth, c.ap):
        c.w.move("G3", cx + r + ALLOW, cy, z, c.feed, (-(r + ALLOW), 0.0))
        z_prev = z
    c.w.move("G3", cx + r + ALLOW, cy, None, c.feed, (-(r + ALLOW), 0.0))
    c.w.move("G1", cx + r, cy, z_prev, c.feed * 0.8)
    c.w.move("G3", cx + r, cy, None, c.feed * 0.8, (-r, 0.0))
    c.w.move("G0", z=SAFE_Z)


def engrave(c: Cut, path: list[Point], depth: float) -> None:
    """Follow a closed outline at a shallow depth (decorative grooves, shapes without text)."""
    c.w.add(f"(ENGRAVE outline of {len(path)} points, depth {fmt(depth)})")
    c.w.move("G0", path[0][0], path[0][1])
    c.w.move("G0", z=SAFE_Z)
    c.w.move("G1", z=-depth, f=c.plunge)
    for px, py in [*path[1:], path[0]]:
        c.w.move("G1", px, py, None, c.feed * 0.7)
    c.w.move("G0", z=SAFE_Z)


def drill(w: Writer, spec: dict[str, Any]) -> None:
    """Drill every point: canned G81/G83 cycles, or explicit pecking when the controller has none (GRBL)."""
    dia, depth, pts, feed = spec["dia"], spec["depth"], spec["points"], spec["feed"]
    peck = round(max(dia * 0.5, 1.0), 1)
    deep = depth > 2 * dia
    w.add(f"(DRILL D{fmt(dia)} x {len(pts)} hole(s), depth {fmt(depth)}{', peck ' + fmt(peck) if deep else ''})")
    w.move("G0", z=SAFE_Z)
    if spec.get("canned", True):
        w.add("G98")
        for i, (px, py) in enumerate(pts):
            w.move("G0", px, py) if i == 0 else w.add(f"X{fmt(px)} Y{fmt(py)}")
            if i == 0:
                w.add(f"G83 Z{fmt(-depth)} R{fmt(RETRACT_R)} Q{fmt(peck)} F{feed}" if deep else f"G81 Z{fmt(-depth)} R{fmt(RETRACT_R)} F{feed}")
        w.add("G80")
        w.feed = None
    else:
        for px, py in pts:
            w.move("G0", px, py)
            w.move("G0", z=RETRACT_R)
            z = 0.0
            while z > -depth + 1e-9:
                z = max(z - (peck if deep else depth), -depth)
                w.move("G1", z=z, f=feed)
                w.move("G0", z=RETRACT_R)
                if z > -depth + 1e-9:
                    w.move("G0", z=z + 0.5)
    w.move("G0", z=CLEAR_Z)
