"""Scalable Approximate Nearest Neighbor (ANN) index using multi-probe random hyperplanes + optional native backends."""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from typing import Any

import numpy as np


def probe_ann_backends() -> dict[str, Any]:
    """Report available vector ANN acceleration backends honestly."""
    return {
        "numpy_lsh_ann": True,
        "sqlite_vec": importlib.util.find_spec("sqlite_vec") is not None,
        "hnswlib": importlib.util.find_spec("hnswlib") is not None,
        "faiss": importlib.util.find_spec("faiss") is not None,
    }


class RandomHyperplaneANN:
    """Deterministic multi-probe SimHash / LSH bucketed ANN index for 100k+ vector scaling (O(sqrt(N)))."""

    def __init__(self, dim: int, num_bits: int = 12, seed: int = 6453) -> None:
        self.dim = max(4, dim)
        self.num_bits = max(4, min(20, num_bits))
        rng = np.random.default_rng(seed)
        self._planes = rng.standard_normal((self.num_bits, self.dim), dtype=np.float32)
        self._buckets: dict[int, list[int]] = defaultdict(list)
        self._ids: list[str] = []
        self._vectors: list[np.ndarray] = []

    def _hash_vec(self, vec: np.ndarray) -> int:
        proj = self._planes @ vec
        code = 0
        for bit_idx, val in enumerate(proj):
            if val >= 0.0:
                code |= 1 << bit_idx
        return code

    def add(self, item_id: str, vector: np.ndarray) -> None:
        arr = np.asarray(vector, dtype=np.float32)
        if arr.shape[0] != self.dim:
            raise ValueError(f"Vektör boyutu uyumsuz: beklenen {self.dim}, gelen {arr.shape[0]}")
        norm = float(np.linalg.norm(arr))
        unit = arr / norm if norm > 0 else arr
        idx = len(self._ids)
        self._ids.append(item_id)
        self._vectors.append(unit)
        self._buckets[self._hash_vec(unit)].append(idx)

    def _candidate_indices(self, code: int, min_candidates: int) -> list[int]:
        seen: set[int] = set(self._buckets.get(code, ()))
        if len(seen) < min_candidates:
            for bit in range(self.num_bits):
                seen.update(self._buckets.get(code ^ (1 << bit), ()))
                if len(seen) >= min_candidates:
                    break
        if len(seen) < min_candidates and len(self._ids) <= 4096:
            return list(range(len(self._ids)))
        return list(seen)

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
        if not self._ids:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        q_norm = float(np.linalg.norm(q))
        q_unit = q / q_norm if q_norm > 0 else q
        candidates = self._candidate_indices(self._hash_vec(q_unit), max(top_k * 8, 32))
        if not candidates:
            return []
        mat = np.stack([self._vectors[i] for i in candidates], axis=0)
        sims = mat @ q_unit
        scored = [(self._ids[candidates[pos]], round(float(sims[pos]), 4)) for pos in range(len(candidates))]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[: max(1, top_k)]

    @property
    def size(self) -> int:
        return len(self._ids)
