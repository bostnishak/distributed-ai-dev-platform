"""3-axis G-code generation from a validated job description: speeds/feeds from a material table, real toolpaths, self-check.

The model only reads the request into numbers (see gcode_chat); everything that ends up in the program (spindle speed,
feed, peck depth, helical entry, coordinates) is computed here (toolpaths live in gcode_paths), and the finished program is
parsed back and checked against the stock before it is shown.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

import gcode_paths as gp
from gcode_patterns import hole_points

# vc: surface speed m/min (carbide end mill), fz_k: chip load per tooth as a fraction of tool diameter,
# drill_vc: HSS/carbide drill surface speed, drill_f: feed per revolution as a fraction of drill diameter, ap_k: depth of cut / diameter
MATERIALS: dict[str, dict[str, Any]] = {
    "aluminum": {"name": "Alüminyum (6061/7075)", "vc": 300, "fz_k": 0.012, "drill_vc": 70, "drill_f": 0.02, "ap_k": 0.5, "coolant": "M8"},
    "steel": {"name": "Çelik (1018/1045)", "vc": 110, "fz_k": 0.006, "drill_vc": 25, "drill_f": 0.012, "ap_k": 0.25, "coolant": "M8"},
    "stainless": {"name": "Paslanmaz çelik (304)", "vc": 65, "fz_k": 0.005, "drill_vc": 15, "drill_f": 0.01, "ap_k": 0.2, "coolant": "M8"},
    "brass": {"name": "Pirinç", "vc": 180, "fz_k": 0.01, "drill_vc": 50, "drill_f": 0.02, "ap_k": 0.4, "coolant": "M8"},
    "plastic": {"name": "Plastik (POM/ABS)", "vc": 250, "fz_k": 0.015, "drill_vc": 60, "drill_f": 0.025, "ap_k": 0.6, "coolant": "M7"},
    "wood": {"name": "Ahşap/MDF", "vc": 400, "fz_k": 0.02, "drill_vc": 60, "drill_f": 0.03, "ap_k": 0.8, "coolant": ""},
    "titanium": {"name": "Titanyum (Ti-6Al-4V)", "vc": 45, "fz_k": 0.004, "drill_vc": 12, "drill_f": 0.008, "ap_k": 0.15, "coolant": "M8"},
}
_ALIASES = (
    ("aluminum", ("alüminyum", "aluminyum", "alüminium", "aluminium", "aluminum", "6061", "7075", "2024")),
    ("stainless", ("paslanmaz", "inox", "stainless", "304", "316")),
    ("titanium", ("titanyum", "titanium", "ti-6al")),
    ("brass", ("pirinç", "pirinc", "brass", "bronz")),
    ("steel", ("çelik", "celik", "steel", "1018", "1045", "4140", "demir")),
    ("plastic", ("plastik", "pom", "delrin", "abs", "naylon", "pvc", "akrilik")),
    ("wood", ("ahşap", "ahsap", "mdf", "kontrplak", "wood")),
)
RAPID_MM_MIN = 5000.0
MAX_SPINDLE = 12000
STANDARD_DIAS = (16.0, 12.0, 10.0, 8.0, 6.0, 5.0, 4.0, 3.0, 2.0)
SAFE_Z, CLEAR_Z = gp.SAFE_Z, gp.CLEAR_Z
MILL_OPS = ("face", "pocket", "round_pocket", "slot")
INCH = 25.4


def material_key(text: str) -> str | None:
    """Material named in the text, or None when there is none (the caller decides how to handle that)."""
    low = (text or "").lower()
    for key, words in _ALIASES:
        for w in words:
            pattern = rf"(?<![\w.]){re.escape(w)}(?!\w)" if w[0].isdigit() else re.escape(w)
            if re.search(pattern, low):
                return key
    return None


@dataclass
class Job:
    material: str
    stock: tuple[float, float, float]
    ops: list[dict[str, Any]]
    mill_dia: float = 10.0
    flutes: int = 3
    flavor: str = "fanuc"
    units: str = "mm"
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class Program:
    lines: list[str]
    tools: list[dict[str, Any]]
    warnings: list[str]
    stats: dict[str, Any] = field(default_factory=dict)


def _f(x: float) -> str:
    return gp.fmt(x)


def auto_mill_dia(ops: list[dict[str, Any]]) -> float:
    """Largest standard end mill that fits every pocket / slot / round pocket (default cap 10 mm)."""
    limits = [10.0]
    for op in ops:
        kind = op["type"]
        if kind == "pocket":
            limits.append(min(float(op["width"]), float(op["length"])) * 0.6)
        elif kind == "round_pocket":
            limits.append(float(op["diameter"]) * 0.5)
        elif kind == "slot":
            limits.append(float(op["width"]) * 0.8)  # a tool narrower than the slot lets the side passes set the width
    cap = min(limits)
    return next((d for d in STANDARD_DIAS if d <= cap + 1e-9), STANDARD_DIAS[-1])


def _speeds(mat: dict[str, Any], dia: float, flutes: int) -> tuple[int, int]:
    rpm = min(MAX_SPINDLE, round(mat["vc"] * 1000 / (math.pi * dia) / 50) * 50)
    feed = round(rpm * flutes * mat["fz_k"] * dia / 10) * 10
    return int(rpm), int(max(feed, 50))


def _drill_speeds(mat: dict[str, Any], dia: float) -> tuple[int, int]:
    rpm = min(MAX_SPINDLE, round(mat["drill_vc"] * 1000 / (math.pi * dia) / 50) * 50)
    return int(max(rpm, 300)), int(max(round(rpm * mat["drill_f"] * dia / 5) * 5, 20))


def _check_holes(job: Job, op: dict[str, Any]) -> None:
    sx, sy, _ = job.stock
    dia = float(op["diameter"])
    for px, py in hole_points(op, job.stock):
        if px - dia / 2 < 2 or px + dia / 2 > sx - 2 or py - dia / 2 < 2 or py + dia / 2 > sy - 2:
            job.warnings.append(f"Ø{_f(dia)} delik ({_f(px)}, {_f(py)}) parçanın kenarına/dışına 2 mm'den yakın; kenar kopabilir ya da delik parçadan taşıyor.")
    if dia >= min(sx, sy):
        job.warnings.append(f"Ø{_f(dia)} delik parça ölçülerine ({_f(sx)}x{_f(sy)}) sığmıyor.")


def _check_job(job: Job) -> None:
    sz, d = job.stock[2], job.mill_dia
    for op in job.ops:
        kind = op["type"]
        if kind in ("hole", "holes"):
            _check_holes(job, op)
        if kind in ("pocket", "round_pocket", "slot", "profile", "face") and float(op.get("depth", 0)) > sz:
            job.warnings.append(f"{kind} derinliği ({_f(float(op['depth']))}) malzeme kalınlığını ({_f(sz)}) aşıyor; kalınlığa indirildi.")
            op["depth"] = sz
        if kind in ("pocket", "round_pocket") and float(op.get("depth", 0)) > 3 * d:
            job.warnings.append(f"{kind} derinliği takım çapının 3 katından fazla (Ø{_f(d)}): takım sapabilir; kısa takım ve ince paso kullan.")
        if kind == "pocket" and min(float(op["width"]), float(op["length"])) < d + 2 * gp.ALLOW:
            job.warnings.append(f"Cep ({_f(float(op['width']))}x{_f(float(op['length']))}) Ø{_f(d)} takım için çok dar.")


def _tool_change(cut: gp.Cut, tools: list[dict[str, Any]], spec: tuple[str, float, int, int, str], flavor: str) -> None:
    """Emit a tool change (spec = label, diameter, rpm, feed, kind); a tool that was used before keeps its number."""
    label, dia, rpm, feed, kind = spec
    w, mat = cut.w, cut.mat or {}
    known = next((t for t in tools if t["name"] == label), None)
    no = known["no"] if known else len(tools) + 1
    if not known:
        tools.append({"no": no, "name": label, "dia": dia, "rpm": rpm, "feed": feed, "kind": kind})
    w.add(f"(T{no} - {label})")
    w.feed = None  # the next cutting move must state its feed again
    w.move("G0", z=CLEAR_Z)
    w.add("M5")
    if flavor == "grbl":
        w.add(f"M0 (CHANGE TOOL: {label})")
    else:
        w.add("G91 G28 Z0")
        w.add("G90")
        w.add(f"T{no} M6")
        w.add(f"G43 H{no} Z{_f(CLEAR_Z)}")
    w.add(f"S{rpm} M3")
    if mat.get("coolant"):
        w.add(mat["coolant"])


def _through(op: dict[str, Any], stock: tuple[float, float, float]) -> float:
    """A contour that goes through the whole thickness is cut 0.3 mm deeper so no skin is left on the bottom."""
    depth = float(op["depth"])
    return depth + 0.3 if depth >= stock[2] - 1e-6 else depth


def _mill(cut: gp.Cut, op: dict[str, Any]) -> None:
    kind, stock = op["type"], cut.stock
    if kind == "face":
        gp.face(cut, float(op.get("depth", 0.5)))
    elif kind == "pocket":
        gp.pocket_rect(cut, (op["x"], op["y"]), (float(op["width"]), float(op["length"])), float(op["depth"]))
    elif kind == "round_pocket":
        gp.pocket_round(cut, (op["x"], op["y"]), float(op["diameter"]), float(op["depth"]))
    elif kind == "slot":
        gp.slot(cut, ((op["x1"], op["y1"]), (op["x2"], op["y2"])), float(op["width"]), float(op["depth"]))
    elif kind == "profile" and op.get("shape") == "circle":
        gp.profile_circle(cut, (op["x"], op["y"]), float(op["diameter"]), _through(op, stock))
    elif kind == "profile":
        part = op.get("width") and op.get("length")
        box = (op["x"] - op["width"] / 2, op["y"] - op["length"] / 2, op["x"] + op["width"] / 2, op["y"] + op["length"] / 2) if part else (0.0, 0.0, stock[0], stock[1])
        gp.profile_rect(cut, box, _through(op, stock))


def _bores(cut: gp.Cut, ops: list[dict[str, Any]]) -> None:
    for op in ops:
        depth = cut.stock[2] + 0.5 if op.get("through", True) else float(op.get("depth", cut.stock[2] / 2))
        for px, py in hole_points(op, cut.stock):
            gp.bore(cut, px, py, float(op["diameter"]), depth)


def _drills(cut: gp.Cut, tools: list[dict[str, Any]], ops: list[dict[str, Any]], flavor: str) -> None:
    sz, mat = cut.stock[2], cut.mat or {}
    for dia in sorted({float(op["diameter"]) for op in ops}, reverse=True):
        drpm, dfeed = _drill_speeds(mat, dia)
        _tool_change(cut, tools, (f"D{_f(dia)} drill", dia, drpm, dfeed, "drill"), flavor)
        for op in (o for o in ops if float(o["diameter"]) == dia):
            tip = 0.3 * dia
            depth = sz + tip + 0.5 if op.get("through", True) else float(op.get("depth", sz / 2)) + tip
            gp.drill(cut.w, {"dia": dia, "depth": depth, "points": hole_points(op, cut.stock), "feed": dfeed, "canned": flavor != "grbl"})


def _header(job: Job, mat: dict[str, Any], w: gp.Writer) -> None:
    sx, sy, sz = job.stock
    w.lines += [f"(PROGRAM - {mat['name']} {_f(sx)}x{_f(sy)}x{_f(sz)} mm)", "(ORIGIN: X0 Y0 = stock lower-left corner, Z0 = stock top surface)", "(SIMULATE BEFORE RUNNING - check work offset and clamping)"]
    if job.flavor == "fanuc":
        w.lines.insert(0, "%\nO0001")
    w.add("G21 G17 G90 G94" + (" G54" if job.flavor != "grbl" else ""))
    w.add("G40 G49 G80" if job.flavor != "grbl" else "G40")


def _footer(job: Job, mat: dict[str, Any], w: gp.Writer) -> None:
    w.add("M5")
    if mat["coolant"]:
        w.add("M9")
    w.move("G0", z=CLEAR_Z)
    if job.flavor != "grbl":
        w.add("G91 G28 Z0")
        w.add("G90")
    w.move("G0", 0, 0)
    w.add("M30")
    if job.flavor == "fanuc":
        w.lines.append("%")


_NUM_WORD_RE = re.compile(r"\b([XYZIJRQF])(-?\d+(?:\.\d+)?)")


def to_inch(lines: list[str]) -> list[str]:
    """Convert a metric program to inch units (G20): coordinates, arc offsets, R/Q and feeds are divided by 25.4."""
    out = []
    for ln in lines:
        if ln.startswith("("):
            out.append(ln)
            continue
        ln = ln.replace("G21", "G20")
        out.append(_NUM_WORD_RE.sub(lambda m: f"{m.group(1)}{round(float(m.group(2)) / INCH, 4):g}", ln))
    return out


def _plan(job: Job) -> tuple[list[dict[str, Any]], ...]:
    """(mill ops, bored holes, drilled holes, engraves, final profiles) in machining order: the contour comes last so the part stays held."""
    is_hole = lambda op: op["type"] in ("hole", "holes")  # noqa: E731
    return (
        [op for op in job.ops if op["type"] in MILL_OPS],
        [op for op in job.ops if is_hole(op) and float(op["diameter"]) > job.mill_dia],
        [op for op in job.ops if is_hole(op) and float(op["diameter"]) <= job.mill_dia],
        [op for op in job.ops if op["type"] == "engrave"],
        [op for op in job.ops if op["type"] == "profile"],
    )


def _cut_for(job: Job, mat: dict[str, Any], w: gp.Writer, dia: float) -> gp.Cut:
    rpm, feed = _speeds(mat, dia, job.flutes)
    return gp.Cut(w, dia, max(0.5, min(dia * mat["ap_k"], dia)), feed, job.stock, rpm, mat)


def _polygon(op: dict[str, Any]) -> list[gp.Point]:
    """Outline points of an engraved shape: regular polygon, star, rectangle or circle (as a 48-gon)."""
    cx, cy, shape = float(op["x"]), float(op["y"]), str(op.get("shape") or "circle")
    r = float(op.get("diameter", 20)) / 2
    if shape == "rect":
        hw, hh = float(op.get("width", 20)) / 2, float(op.get("length", 20)) / 2
        return [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    if shape == "star":
        n = int(op.get("points", 5))
        radii = [(r if k % 2 == 0 else r * 0.4, math.pi / 2 + math.pi * k / n) for k in range(2 * n)]
        return [(cx + rr * math.cos(a), cy + rr * math.sin(a)) for rr, a in radii]
    n = 48 if shape == "circle" else max(3, int(op.get("sides", 6)))
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _engrave_phase(cut: gp.Cut, tools: list[dict[str, Any]], ops: list[dict[str, Any]], flavor: str) -> None:
    _tool_change(cut, tools, ("D3 engraving end mill Z2", cut.dia, cut.rpm, int(cut.feed * 0.5), "mill"), flavor)
    for op in ops:
        gp.engrave(cut, _polygon(op), float(op.get("depth", 0.5)))


def generate(job: Job) -> Program:
    mat = MATERIALS[job.material]
    _check_job(job)
    if any(op.get("through", True) for op in job.ops if op["type"] in ("hole", "holes")) or any(op["type"] == "profile" for op in job.ops):
        job.warnings.append("Delik/kontur parçayı baştan başa geçiyor: parçanın altına altlık (kurban plaka) koy ve mengene/aparatı takımın inebileceği derinliğin dışında tut.")
    w, tools = gp.Writer(), []
    _header(job, mat, w)
    mill, bored, drilled, engraves, profiles = _plan(job)
    cut = _cut_for(job, mat, w, job.mill_dia)
    label = f"D{_f(job.mill_dia)} end mill Z{job.flutes}"
    if mill or bored:
        _tool_change(cut, tools, (label, job.mill_dia, cut.rpm, cut.feed, "mill"), job.flavor)
        for op in mill:
            _mill(cut, op)
        _bores(cut, bored)
    _drills(cut, tools, drilled, job.flavor)
    if engraves:
        _engrave_phase(_cut_for(job, mat, w, 3.0), tools, engraves, job.flavor)
    if profiles:
        _tool_change(cut, tools, (label, job.mill_dia, cut.rpm, cut.feed, "mill"), job.flavor)
        for op in profiles:
            _mill(cut, op)
    _footer(job, mat, w)
    prog = Program(to_inch(w.lines) if job.units == "inch" else w.lines, tools, job.warnings)
    prog.stats = verify(Program(w.lines, tools, job.warnings), job)
    return prog


_WORD_RE = re.compile(r"([XYZFIJ])(-?\d+(?:\.\d+)?)")


def _arc_length(start: tuple[float, float], end: tuple[float, float], words: dict[str, float], ccw: bool, dz: float) -> tuple[float, list[float]]:
    """(3D length, [xmin, ymin, xmax, ymax]) of a G2/G3 move; a move that ends where it started is a full circle."""
    (x, y), (nx, ny) = start, end
    i, j = words.get("I", 0.0), words.get("J", 0.0)
    r, cx, cy = math.hypot(i, j), x + i, y + j
    if math.hypot(nx - x, ny - y) < 1e-6:
        return math.hypot(2 * math.pi * r, dz), [cx - r, cy - r, cx + r, cy + r]
    a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
    sweep = (a1 - a0) % (2 * math.pi) if ccw else (a0 - a1) % (2 * math.pi)
    return math.hypot(r * sweep, dz), [min(x, nx), min(y, ny), max(x, nx), max(y, ny)]


def _scan(prog: Program) -> dict[str, Any]:
    """Walk the program like a controller: positions, modal motion, feed; returns lengths, time, deepest Z, bounds."""
    x = y = z = 0.0
    f, modal = 1000.0, "G0"
    cut = rapid = minutes = minz = 0.0
    bounds = [1e9, 1e9, -1e9, -1e9]
    for raw in prog.lines:
        line = re.sub(r"^N\d+\s*", "", re.sub(r"\(.*?\)", "", raw))
        if re.search(r"\bG(28|53)\b", line):
            continue
        if g := re.match(r"\s*(?:G9[89]\s*)?(G[0-3]|G8[013])\b", line):
            modal = g.group(1)
        words = {k: float(v) for k, v in _WORD_RE.findall(line)}
        f = words.get("F", f)
        if not any(k in words for k in "XYZ") or (modal in ("G81", "G83") and "Z" not in words and "X" not in words):
            continue
        nx, ny, nz = words.get("X", x), words.get("Y", y), words.get("Z", z)
        dist = math.dist((x, y, z), (nx, ny, nz))
        if modal in ("G81", "G83"):
            dist = abs(nz - z) * 2
        elif modal in ("G2", "G3"):
            dist, arc = _arc_length((x, y), (nx, ny), words, modal == "G3", nz - z)
            bounds = [min(bounds[0], arc[0]), min(bounds[1], arc[1]), max(bounds[2], arc[2]), max(bounds[3], arc[3])]
        if modal == "G0":
            rapid, minutes = rapid + dist, minutes + dist / RAPID_MM_MIN
        else:
            cut, minutes = cut + dist, minutes + dist / max(f, 1.0)
            bounds = [min(bounds[0], nx), min(bounds[1], ny), max(bounds[2], nx), max(bounds[3], ny)]
        x, y, z = nx, ny, nz
        minz = min(minz, nz)
    return {"cut": cut, "rapid": rapid, "minutes": minutes, "minz": minz, "bounds": bounds}


def verify(prog: Program, job: Job) -> dict[str, Any]:
    """Parse the program back: bounds, deepest cut, estimated machining time; problems are appended to the warnings."""
    s = _scan(prog)
    sx, sy, sz = job.stock
    bounds, minz = s["bounds"], s["minz"]
    reach = max((t["dia"] for t in prog.tools if t["kind"] == "mill"), default=0) / 2
    if bounds[2] > -1e8 and (bounds[0] < -reach - 3.5 or bounds[1] < -reach - 3.5 or bounds[2] > sx + reach + 3.5 or bounds[3] > sy + reach + 3.5):
        prog.warnings.append("Takım yolu parça sınırlarının dışına taşıyor; ölçüleri kontrol et.")
    if minz < -(sz + 0.3 * max([t["dia"] for t in prog.tools] or [0]) + 1.6):
        prog.warnings.append("Programdaki en derin Z, malzeme kalınlığını fazla aşıyor.")
    return {"cut_mm": round(s["cut"]), "rapid_mm": round(s["rapid"]), "minutes": round(s["minutes"] + 0.5 * len(prog.tools), 1), "min_z": round(minz, 2), "bounds": [round(b, 1) for b in bounds]}
