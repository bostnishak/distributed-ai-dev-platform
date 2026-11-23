"""Cluster C ([M37]): Parallel Map-Reduce Task Split and Distributed Synthesis Engine.

Splits large document analysis or multi-file software engineering workloads across online
agents (Map) and merges/deduplicates parallel agent findings with consistency verification
and empirical speedup calculation (Reduce).
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any


def split_document_or_tasks_for_map(
    text_or_items: str | list[Any],
    chunk_count: int = 4,
) -> list[dict[str, Any]]:
    """Split a long document string or a list of tasks/files into balanced map shards."""
    target_chunks = max(1, int(chunk_count))

    if isinstance(text_or_items, str):
        raw_text = text_or_items.strip()
        if not raw_text:
            return []

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw_text) if p.strip()]
        if len(paragraphs) < target_chunks:
            paragraphs = [line.strip() for line in raw_text.splitlines() if line.strip()]

        if not paragraphs:
            return [
                {
                    "chunk_index": 0,
                    "chunk_id": "map-chunk-01",
                    "item_type": "text",
                    "content": raw_text,
                    "char_count": len(raw_text),
                    "item_count": 1,
                }
            ]

        actual_chunks = min(target_chunks, len(paragraphs))
        buckets: list[list[str]] = [[] for _ in range(actual_chunks)]
        bucket_chars = [0] * actual_chunks

        # Greedy balanced packing by paragraph order
        batch_size = math.ceil(len(paragraphs) / actual_chunks)
        for idx, para in enumerate(paragraphs):
            b_idx = min(idx // batch_size, actual_chunks - 1)
            buckets[b_idx].append(para)
            bucket_chars[b_idx] += len(para)

        shards: list[dict[str, Any]] = []
        for _idx, bucket in enumerate(buckets):
            if not bucket:
                continue
            joined = "\n\n".join(bucket)
            shards.append(
                {
                    "chunk_index": len(shards),
                    "chunk_id": f"map-chunk-{len(shards) + 1:02d}",
                    "item_type": "text",
                    "content": joined,
                    "items": bucket,
                    "char_count": len(joined),
                    "item_count": len(bucket),
                }
            )
        return shards

    if isinstance(text_or_items, list):
        items = [x for x in text_or_items if x is not None]
        if not items:
            return []
        actual_chunks = min(target_chunks, len(items))
        batch_size = math.ceil(len(items) / actual_chunks)
        shards = []
        for c_idx in range(actual_chunks):
            slice_items = items[c_idx * batch_size : (c_idx + 1) * batch_size]
            if not slice_items:
                continue
            serialized = "\n".join(str(x) for x in slice_items)
            shards.append(
                {
                    "chunk_index": len(shards),
                    "chunk_id": f"map-chunk-{len(shards) + 1:02d}",
                    "item_type": "task_list",
                    "content": serialized,
                    "items": slice_items,
                    "char_count": len(serialized),
                    "item_count": len(slice_items),
                }
            )
        return shards

    raise TypeError("text_or_items must be a str or list")


def reduce_mapped_results(mapped_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge parallel agent map outputs, deduplicate findings, verify numerical consistency,
    and compute empirical parallel speedup factor.
    """
    if not mapped_results:
        return {
            "chunk_count": 0,
            "unique_findings_count": 0,
            "deduplicated_findings": [],
            "merged_summary": "",
            "is_consistent": True,
            "conflicts": [],
            "sequential_latency_ms": 0.0,
            "parallel_wall_ms": 0.0,
            "speedup_factor": 1.0,
            "agents_used": [],
        }

    dedup_findings: list[str] = []
    seen_hashes: set[str] = set()
    summaries: list[str] = []
    agents_used: list[str] = []
    latencies: list[float] = []
    key_value_claims: dict[str, set[str]] = {}
    conflicts: list[dict[str, Any]] = []

    kv_pattern = re.compile(r"\b([A-Za-z0-9_/-]{3,25})\s*(?:=|:)\s*(\d+(?:\.\d+)?(?:\s*(?:mm|MPa|kW|HRC|TL|EUR|USD|%))?)")

    for idx, res in enumerate(mapped_results):
        if not isinstance(res, dict):
            continue
        agent_id = str(res.get("agent_id") or res.get("worker") or f"agent-{idx + 1:02d}").strip()
        if agent_id not in agents_used:
            agents_used.append(agent_id)

        lat = float(res.get("latency_ms", res.get("duration_ms", 250.0)))
        latencies.append(max(1.0, lat))

        text_body = str(res.get("summary") or res.get("output") or res.get("content") or "").strip()
        if text_body:
            summaries.append(text_body)

        raw_findings = res.get("findings") or res.get("items") or []
        if isinstance(raw_findings, str):
            raw_findings = [line.strip() for line in raw_findings.splitlines() if line.strip()]
        elif not isinstance(raw_findings, list):
            raw_findings = []

        if not raw_findings and text_body:
            raw_findings = [s.strip() for s in re.split(r"[.\n]+", text_body) if len(s.strip()) >= 8]

        for finding in raw_findings:
            f_str = str(finding).strip()
            if not f_str:
                continue
            norm = re.sub(r"\s+", " ", f_str.lower())
            digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
            if digest not in seen_hashes:
                seen_hashes.add(digest)
                dedup_findings.append(f_str)

            for match in kv_pattern.finditer(f_str):
                k_name = match.group(1).strip().lower()
                v_val = match.group(2).strip()
                bucket = key_value_claims.setdefault(k_name, set())
                bucket.add(v_val)

    for k_name, vals in key_value_claims.items():
        if len(vals) > 1:
            conflicts.append({"parameter": k_name, "conflicting_values": sorted(vals)})

    seq_latency = sum(latencies) if latencies else 0.0
    par_wall = max(latencies) if latencies else 0.0
    speedup = round(seq_latency / par_wall, 3) if par_wall > 0 else 1.0

    return {
        "chunk_count": len(mapped_results),
        "unique_findings_count": len(dedup_findings),
        "deduplicated_findings": dedup_findings,
        "merged_summary": "\n".join(summaries),
        "is_consistent": len(conflicts) == 0,
        "conflicts": conflicts,
        "sequential_latency_ms": round(seq_latency, 2),
        "parallel_wall_ms": round(par_wall, 2),
        "speedup_factor": max(1.0, speedup),
        "agents_used": agents_used,
    }
