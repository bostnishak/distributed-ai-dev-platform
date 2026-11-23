"""Cluster D ([M52]): OPC-UA / MTConnect Live CNC Machine Telemetry, OEE Calculator,
and Chatter / Spindle Overload Anomaly Detector.
"""

from __future__ import annotations

from typing import Any


def ingest_machine_telemetry(
    samples: list[dict[str, Any]],
    ideal_cycle_time_sec: float = 45.0,
) -> dict[str, Any]:
    """Analyze OPC-UA / MTConnect CNC telemetry samples (``spindle_load_pct``, ``feed_override_pct``,
    ``vibration_mm_s``, ``cycle_time_sec``), compute OEE (``availability * performance * quality``),
    and flag chatter or spindle overload anomalies.
    """
    if not samples:
        raise ValueError("samples list must not be empty")

    loads: list[float] = []
    feeds: list[float] = []
    vibrations: list[float] = []
    cycles: list[float] = []
    anomalies: list[dict[str, Any]] = []

    running_count = 0
    good_part_count = 0

    for idx, sample in enumerate(samples):
        load_pct = float(sample.get("spindle_load_pct", 55.0))
        feed_pct = float(sample.get("feed_override_pct", 100.0))
        vib_mm_s = float(sample.get("vibration_mm_s", 1.8))
        cycle_sec = float(sample.get("cycle_time_sec", ideal_cycle_time_sec))
        is_running = bool(sample.get("is_running", cycle_sec > 0 and load_pct > 0))
        scrap = bool(sample.get("is_scrap", False))

        loads.append(load_pct)
        feeds.append(feed_pct)
        vibrations.append(vib_mm_s)
        cycles.append(max(0.1, cycle_sec))

        if is_running:
            running_count += 1
        if not scrap and load_pct <= 105.0 and vib_mm_s <= 6.5:
            good_part_count += 1

        if load_pct >= 85.0:
            anomalies.append(
                {
                    "sample_index": idx,
                    "type": "SPINDLE_OVERLOAD",
                    "severity": "CRITICAL" if load_pct >= 95.0 else "HIGH",
                    "value": round(load_pct, 2),
                    "message": f"Spindle load {load_pct:.1f}% exceeds 85% threshold.",
                }
            )
        if vib_mm_s >= 4.5:
            anomalies.append(
                {
                    "sample_index": idx,
                    "type": "CHATTER_VIBRATION",
                    "severity": "CRITICAL" if vib_mm_s >= 6.5 else "HIGH",
                    "value": round(vib_mm_s, 2),
                    "message": f"Vibration {vib_mm_s:.2f} mm/s RMS indicates regenerative chatter.",
                }
            )

    n = len(samples)
    avg_load = round(sum(loads) / n, 2)
    avg_feed = round(sum(feeds) / n, 2)
    avg_vib = round(sum(vibrations) / n, 3)
    avg_cycle = round(sum(cycles) / n, 2)

    availability = min(1.0, max(0.05, running_count / n))
    ideal_sec = max(1.0, float(ideal_cycle_time_sec))
    performance = min(1.0, max(0.05, ideal_sec / max(avg_cycle, ideal_sec * 0.85)))
    quality = min(1.0, max(0.05, good_part_count / n))
    oee = round(availability * performance * quality, 4)

    return {
        "sample_count": n,
        "mean_spindle_load_pct": avg_load,
        "max_spindle_load_pct": round(max(loads), 2),
        "mean_feed_override_pct": avg_feed,
        "mean_vibration_mm_s": avg_vib,
        "max_vibration_mm_s": round(max(vibrations), 3),
        "mean_cycle_time_sec": avg_cycle,
        "availability": round(availability, 4),
        "performance": round(performance, 4),
        "quality": round(quality, 4),
        "oee": oee,
        "oee_percent": round(oee * 100.0, 2),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "has_chatter_or_overload": len(anomalies) > 0,
    }


__all__ = ["ingest_machine_telemetry"]
