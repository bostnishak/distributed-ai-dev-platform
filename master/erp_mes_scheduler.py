"""Enterprise ERP / MES Minimal-Waste Nesting Optimizer and Finite-Capacity Job-Shop Scheduler.

Implements Cluster D modules [M53] and [M54]:
- 1D Bar and 2D Sheet minimal-waste nesting using First-Fit Decreasing (FFD) bin-packing with kerf allowance.
- Finite-capacity CNC Job-Shop scheduler across OP10..OP50 with precedence constraints, setup times,
  due-date / SPT prioritization, machine utilization %, and Gantt chart bars.
"""

from __future__ import annotations

from typing import Any


def _expand_1d_parts(parts: list[dict[str, Any]], stock_len: float) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for idx, p in enumerate(parts or []):
        part_id = str(p.get("part_id") or p.get("name") or f"P-{idx + 1:02d}")
        length = float(p.get("length_mm", p.get("length", 0.0)))
        qty = int(p.get("quantity", p.get("qty", 1)))
        if length <= 0 or qty <= 0:
            continue
        if length > stock_len:
            raise ValueError(f"Part {part_id} length {length} mm exceeds stock_length_mm {stock_len} mm")
        for copy_no in range(1, qty + 1):
            expanded.append({"part_id": part_id, "instance_id": f"{part_id}#{copy_no}", "length_mm": round(length, 3)})
    expanded.sort(key=lambda item: item["length_mm"], reverse=True)
    return expanded


def _place_1d_item(bars: list[dict[str, Any]], item: dict[str, Any], stock_len: float, kerf: float) -> None:
    item_len = item["length_mm"]
    for bar in bars:
        needed = item_len if not bar["cuts"] else (item_len + kerf)
        if bar["remaining_mm"] >= needed - 1e-9:
            if bar["cuts"]:
                bar["kerf_loss_mm"] = round(bar["kerf_loss_mm"] + kerf, 3)
            bar["cuts"].append(item)
            bar["used_net_mm"] = round(bar["used_net_mm"] + item_len, 3)
            bar["remaining_mm"] = round(max(bar["remaining_mm"] - needed, 0.0), 3)
            return
    bars.append(
        {
            "bar_index": len(bars) + 1,
            "stock_length_mm": stock_len,
            "cuts": [item],
            "used_net_mm": round(item_len, 3),
            "kerf_loss_mm": 0.0,
            "remaining_mm": round(stock_len - item_len, 3),
        }
    )


def optimize_1d_bar_nesting(
    stock_length_mm: float,
    kerf_mm: float,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Optimize 1D bar cutting layout using First-Fit Decreasing (FFD) bin-packing with saw kerf allowance."""
    stock_len = float(stock_length_mm)
    if stock_len <= 0:
        raise ValueError("stock_length_mm must be positive")
    kerf = max(float(kerf_mm), 0.0)

    expanded_items = _expand_1d_parts(parts, stock_len)
    bars: list[dict[str, Any]] = []
    for item in expanded_items:
        _place_1d_item(bars, item, stock_len, kerf)

    total_stock_mm = len(bars) * stock_len
    total_net_part_mm = sum(b["used_net_mm"] for b in bars)
    total_kerf_mm = sum(b["kerf_loss_mm"] for b in bars)
    total_scrap_mm = max(total_stock_mm - total_net_part_mm - total_kerf_mm, 0.0)
    utilization_pct = round((total_net_part_mm / total_stock_mm) * 100.0, 2) if total_stock_mm > 0 else 0.0
    scrap_pct = round(100.0 - utilization_pct, 2) if total_stock_mm > 0 else 0.0

    for b in bars:
        b["utilization_percent"] = round((b["used_net_mm"] / stock_len) * 100.0, 2)
        b["scrap_mm"] = b["remaining_mm"]

    return {
        "stock_length_mm": stock_len,
        "kerf_mm": kerf,
        "total_parts_nested": len(expanded_items),
        "bar_count": len(bars),
        "bars": bars,
        "total_stock_mm": round(total_stock_mm, 3),
        "total_net_part_mm": round(total_net_part_mm, 3),
        "total_kerf_mm": round(total_kerf_mm, 3),
        "total_scrap_mm": round(total_scrap_mm, 3),
        "material_utilization_percent": utilization_pct,
        "scrap_percent": scrap_pct,
    }


def _expand_2d_parts(parts: list[dict[str, Any]], sw: float, sh: float) -> list[dict[str, Any]]:
    rects: list[dict[str, Any]] = []
    for idx, p in enumerate(parts or []):
        part_id = str(p.get("part_id") or p.get("name") or f"S-{idx + 1:02d}")
        w = float(p.get("width_mm", p.get("width", 0.0)))
        h = float(p.get("height_mm", p.get("height", p.get("length_mm", 0.0))))
        qty = int(p.get("quantity", p.get("qty", 1)))
        if w <= 0 or h <= 0 or qty <= 0:
            continue
        if h > sh and w <= sh and h <= sw:
            w, h = h, w
        if w > sw or h > sh:
            raise ValueError(f"Part {part_id} ({w}x{h} mm) exceeds sheet ({sw}x{sh} mm)")
        for copy_no in range(1, qty + 1):
            rects.append(
                {
                    "part_id": part_id,
                    "instance_id": f"{part_id}#{copy_no}",
                    "width_mm": round(w, 3),
                    "height_mm": round(h, 3),
                    "area_mm2": round(w * h, 3),
                }
            )
    rects.sort(key=lambda r: (r["height_mm"], r["area_mm2"]), reverse=True)
    return rects


def _make_2d_placement(rect: dict[str, Any], x_pos: float, y_pos: float) -> dict[str, Any]:
    return {
        "part_id": rect["part_id"],
        "instance_id": rect["instance_id"],
        "x_mm": round(x_pos, 3),
        "y_mm": round(y_pos, 3),
        "width_mm": rect["width_mm"],
        "height_mm": rect["height_mm"],
    }


def _try_place_on_sheet(sheet: dict[str, Any], rect: dict[str, Any], dims: tuple[float, float, float]) -> bool:
    sw, sh, kerf = dims
    rw, rh = rect["width_mm"], rect["height_mm"]
    for shelf in sheet["shelves"]:
        req_w = rw if shelf["cursor_x"] == 0 else (rw + kerf)
        if rh <= shelf["height_mm"] and (shelf["cursor_x"] + req_w) <= sw + 1e-9:
            x_pos = shelf["cursor_x"] if shelf["cursor_x"] == 0 else (shelf["cursor_x"] + kerf)
            shelf["cursor_x"] = round(x_pos + rw, 3)
            sheet["placements"].append(_make_2d_placement(rect, x_pos, shelf["y_mm"]))
            sheet["used_area_mm2"] = round(sheet["used_area_mm2"] + rect["area_mm2"], 3)
            return True

    next_y = 0.0 if not sheet["shelves"] else (sheet["shelves"][-1]["y_mm"] + sheet["shelves"][-1]["height_mm"] + kerf)
    if (next_y + rh) <= sh + 1e-9:
        sheet["shelves"].append({"y_mm": round(next_y, 3), "height_mm": rh, "cursor_x": rw})
        sheet["placements"].append(_make_2d_placement(rect, 0.0, next_y))
        sheet["used_area_mm2"] = round(sheet["used_area_mm2"] + rect["area_mm2"], 3)
        return True
    return False


def optimize_2d_sheet_nesting(
    sheet_width_mm: float,
    sheet_height_mm: float,
    kerf_mm: float,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Optimize 2D rectangular sheet nesting using shelf First-Fit Decreasing (FFD) with kerf allowance."""
    sw = float(sheet_width_mm)
    sh = float(sheet_height_mm)
    if sw <= 0 or sh <= 0:
        raise ValueError("Sheet dimensions must be positive")
    kerf = max(float(kerf_mm), 0.0)

    rects = _expand_2d_parts(parts, sw, sh)
    sheets: list[dict[str, Any]] = []
    dims = (sw, sh, kerf)
    for rect in rects:
        if any(_try_place_on_sheet(sheet, rect, dims) for sheet in sheets):
            continue
        sheets.append(
            {
                "sheet_index": len(sheets) + 1,
                "sheet_width_mm": sw,
                "sheet_height_mm": sh,
                "shelves": [{"y_mm": 0.0, "height_mm": rect["height_mm"], "cursor_x": rect["width_mm"]}],
                "placements": [_make_2d_placement(rect, 0.0, 0.0)],
                "used_area_mm2": rect["area_mm2"],
            }
        )

    sheet_area = sw * sh
    total_sheet_area = len(sheets) * sheet_area
    total_used_area = sum(s["used_area_mm2"] for s in sheets)
    utilization_pct = round((total_used_area / total_sheet_area) * 100.0, 2) if total_sheet_area > 0 else 0.0
    for s in sheets:
        s["utilization_percent"] = round((s["used_area_mm2"] / sheet_area) * 100.0, 2)

    return {
        "sheet_width_mm": sw,
        "sheet_height_mm": sh,
        "kerf_mm": kerf,
        "total_parts_nested": len(rects),
        "sheet_count": len(sheets),
        "sheets": sheets,
        "material_utilization_percent": utilization_pct,
        "scrap_percent": round(100.0 - utilization_pct, 2) if total_sheet_area > 0 else 0.0,
    }


def _resolve_op_candidates(op: dict[str, Any], avail_machines: list[str], machine_set: set[str]) -> list[str]:
    pref_machine = op.get("machine") or op.get("preferred_machine")
    eligible = op.get("eligible_machines")
    if eligible and isinstance(eligible, list):
        candidates = [str(m) for m in eligible if str(m) in machine_set]
    elif pref_machine and str(pref_machine) in machine_set:
        candidates = [str(pref_machine)]
    else:
        candidates = list(avail_machines)
    return candidates or list(avail_machines)


def _normalize_job_operations(
    jobs: list[dict[str, Any]],
    avail_machines: list[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, float]]:
    machine_set = set(avail_machines)
    pending_ops: dict[str, list[dict[str, Any]]] = {}
    job_last_end: dict[str, float] = {}
    for j_idx, job in enumerate(jobs or []):
        job_id = str(job.get("job_id") or job.get("id") or f"JOB-{j_idx + 1:03d}")
        due_min = float(job.get("due_date_min", job.get("due_min", 1440.0)))
        qty = max(int(job.get("quantity", job.get("qty", 1))), 1)
        job_last_end[job_id] = 0.0
        raw_ops = job.get("operations") or [
            {
                "op_code": "OP10",
                "machine": job.get("machine", avail_machines[0]),
                "setup_min": float(job.get("setup_min", 15.0)),
                "run_min": float(job.get("run_min", 30.0)),
            }
        ]
        op_list: list[dict[str, Any]] = []
        for op_idx, op in enumerate(raw_ops):
            setup_m = max(float(op.get("setup_min", 10.0)), 0.0)
            cycle_m = max(float(op.get("run_min", op.get("cycle_min", 20.0))), 0.1)
            op_list.append(
                {
                    "job_id": job_id,
                    "op_code": str(op.get("op_code") or op.get("op") or f"OP{(op_idx + 1) * 10}"),
                    "op_order": op_idx,
                    "setup_min": setup_m,
                    "run_min": round(cycle_m * qty, 2),
                    "duration_min": round(setup_m + cycle_m * qty, 2),
                    "candidate_machines": _resolve_op_candidates(op, avail_machines, machine_set),
                    "due_min": due_min,
                }
            )
        pending_ops[job_id] = op_list
    return pending_ops, job_last_end


def _pick_next_operation(
    pending_ops_by_job: dict[str, list[dict[str, Any]]],
    job_last_end_min: dict[str, float],
    machine_ready_min: dict[str, float],
) -> tuple[float, float, float, str, dict[str, Any], str]:
    ready_candidates: list[tuple[float, float, float, str, dict[str, Any], str]] = []
    for job_id, ops in pending_ops_by_job.items():
        if not ops:
            continue
        next_op = ops[0]
        pred_end = job_last_end_min[job_id]
        best_machine = min(
            next_op["candidate_machines"],
            key=lambda m: max(machine_ready_min[m], pred_end) + next_op["duration_min"],
        )
        earliest_start = max(machine_ready_min[best_machine], pred_end)
        ready_candidates.append(
            (earliest_start, next_op["due_min"], next_op["duration_min"], job_id, next_op, best_machine)
        )
    ready_candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return ready_candidates[0]


def schedule_cnc_job_shop(
    jobs: list[dict[str, Any]],
    machines: list[str],
) -> dict[str, Any]:
    """Schedule multi-operation CNC jobs (OP10..OP50) across finite-capacity machines.

    Respects operation precedence constraints, setup times, and due dates using an
    Earliest Due Date (EDD) + Shortest Processing Time (SPT) dispatching heuristic.
    Returns scheduled start/end minutes, makespan, machine utilization %, and Gantt chart bars.
    """
    avail_machines = [m.strip() for m in (machines or []) if m.strip()]
    if not avail_machines:
        avail_machines = ["CNC-TURN-01", "CNC-MILL-01", "CNC-5AX-01"]

    machine_ready_min: dict[str, float] = {m: 0.0 for m in avail_machines}
    machine_busy_min: dict[str, float] = {m: 0.0 for m in avail_machines}
    pending_ops_by_job, job_last_end_min = _normalize_job_operations(jobs, avail_machines)
    gantt_bars: list[dict[str, Any]] = []

    while any(pending_ops_by_job.values()):
        start_min, due_min, duration_min, chosen_job_id, chosen_op, chosen_machine = _pick_next_operation(
            pending_ops_by_job, job_last_end_min, machine_ready_min
        )
        end_min = round(start_min + duration_min, 2)
        machine_ready_min[chosen_machine] = end_min
        machine_busy_min[chosen_machine] = round(machine_busy_min[chosen_machine] + duration_min, 2)
        job_last_end_min[chosen_job_id] = end_min
        pending_ops_by_job[chosen_job_id].pop(0)
        gantt_bars.append(
            {
                "job_id": chosen_job_id,
                "op_code": chosen_op["op_code"],
                "machine": chosen_machine,
                "start_min": round(start_min, 2),
                "end_min": end_min,
                "setup_min": chosen_op["setup_min"],
                "run_min": chosen_op["run_min"],
                "duration_min": duration_min,
                "due_min": due_min,
                "is_late": end_min > due_min,
            }
        )

    makespan_min = max((bar["end_min"] for bar in gantt_bars), default=0.0)
    machine_utilization = {
        m: round((machine_busy_min[m] / makespan_min) * 100.0, 2) if makespan_min > 0 else 0.0
        for m in avail_machines
    }

    return {
        "machines": avail_machines,
        "total_operations_scheduled": len(gantt_bars),
        "makespan_min": round(makespan_min, 2),
        "machine_utilization_percent": machine_utilization,
        "gantt_bars": gantt_bars,
    }
