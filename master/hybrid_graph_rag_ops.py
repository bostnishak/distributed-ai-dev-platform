"""Cluster C operational kernels: embeddings, BM25+RRF fusion, KG extraction/BFS, image fingerprinting & citation verification."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import struct
from collections import deque
from collections.abc import Sequence
from typing import Any

import numpy as np
from PIL import Image

FALLBACK_EMBED_DIM = 256
IMAGE_FINGERPRINT_DIM = 64

_ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Material",
        re.compile(
            r"\b(?:AISI\s*\d{3,4}[A-Z]*|SAE\s*\d{4}|Al(?:üminyum|uminum)?\s*\d{4}(?:-T\d+)?|"
            r"Ti-6Al-4V|Inconel\s*\d{3}|CK45|C45|42CrMo4|St\s*\d{2}(?:-\d)?|1\.\d{4})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Standard",
        re.compile(
            r"\b(?:ISO\s*\d{3,5}(?:-[a-zA-Z0-9]+)?|AS\s*910[02]|DIN\s*\d{3,5}|"
            r"ASME\s*Y14\.\d+|ASTM\s*[A-Z]\d+|KVKK|GDPR)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Tolerance",
        re.compile(
            r"(?:±\s*\d+(?:\.\d+)?\s*mm|\b[HhGgKkFfMmJj]\d{1,2}\b|"
            r"\bRa\s*\d+(?:\.\d+)?|\bCp[k]?\s*(?:>=|≥|=)\s*\d+(?:\.\d+)?|\b6[HGhg]\b)",
        ),
    ),
    (
        "Tool",
        re.compile(
            r"\b(?:TiAlN|karbür\s+rayba|karbür\s+uç|HSS-E|parmak\s+freze|mikrometrik\s+bara|"
            r"CMM|tampon\s+mastar|kılavuz)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Operation",
        re.compile(
            r"\b(?:OP\d{2}|tornalama|frezeleme|delik\s+delme|raybalama|kılavuz\s+çekme|"
            r"taşlama|balonlama|FAI)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Module",
        re.compile(
            r"\b(?:FastAPI|SQLite|PyMuPDF|Thompson\s+Sampling|GraphRAG|Vision-RAG|QLoRA|DPO|"
            r"Fanuc|Siemens\s+Sinumerik|Heidenhain)\b",
            re.IGNORECASE,
        ),
    ),
]

_RELATION_MAP: dict[tuple[str, str], str] = {
    ("Material", "Tolerance"): "REQUIRES_TOLERANCE",
    ("Tolerance", "Material"): "APPLIES_TO_MATERIAL",
    ("Material", "Tool"): "MACHINED_WITH_TOOL",
    ("Tool", "Material"): "CUTS_MATERIAL",
    ("Material", "Operation"): "PROCESSED_BY_OPERATION",
    ("Operation", "Tool"): "USES_TOOL",
    ("Tool", "Operation"): "SUPPORTS_OPERATION",
    ("Operation", "Tolerance"): "ACHIEVES_TOLERANCE",
    ("Tolerance", "Tool"): "VERIFIED_OR_CUT_BY",
    ("Standard", "Tolerance"): "DEFINES_TOLERANCE",
    ("Tolerance", "Standard"): "GOVERNED_BY_STANDARD",
    ("Standard", "Operation"): "GOVERNS_OPERATION",
    ("Material", "Standard"): "COMPLIES_WITH_STANDARD",
}

_NUM_CLAIM_RE = re.compile(r"(?:±\s*)?\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9çğıöşü]+(?:[.\-/][a-z0-9çğıöşü]+)*", (text or "").lower())


def deterministic_ngram_embedding(text: str, dim: int = FALLBACK_EMBED_DIM) -> list[float]:
    """Compute a fast (<1ms) deterministic L2-normalized character/word n-gram embedding vector."""
    vec = [0.0] * dim
    norm_text = (text or "").lower().strip()
    if not norm_text:
        return vec

    tokens = _tokenize(norm_text)
    features: list[tuple[str, float]] = []
    for tok in tokens:
        features.append((f"w:{tok}", 2.0))
        padded = f"<{tok}>"
        for n in (3, 4):
            for i in range(max(0, len(padded) - n + 1)):
                features.append((f"c{n}:{padded[i : i + n]}", 1.0))

    for idx in range(len(tokens) - 1):
        features.append((f"b:{tokens[idx]}_{tokens[idx + 1]}", 1.5))

    for feat, weight in features:
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        h_val = int.from_bytes(digest, "little")
        bucket = h_val % dim
        sign = 1.0 if ((h_val >> 63) & 1) == 0 else -1.0
        vec[bucket] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [round(v / norm, 6) for v in vec]
    return vec


def _pack_vector(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack_vector(blob: bytes) -> list[float]:
    if not blob:
        return []
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob[: count * 4]))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        min_len = min(len(a), len(b))
        a = a[:min_len]
        b = b[:min_len]
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(dot / (na * nb))


def _relation_for_pair(src_type: str, dst_type: str) -> str:
    return _RELATION_MAP.get((src_type, dst_type), "RELATED_TO")


def compute_image_fingerprint(raw_bytes: bytes) -> list[float]:
    """Compute a L2-normalized 64-dimensional perceptual + edge-orientation fingerprint."""
    if not raw_bytes:
        raise ValueError("raw_bytes cannot be empty")
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            gray = img.convert("L").resize((64, 64), Image.Resampling.BILINEAR)
            arr = np.asarray(gray, dtype=np.float32) / 255.0
    except (OSError, ValueError, TypeError, RuntimeError, SyntaxError):
        digest = hashlib.sha512(raw_bytes).digest()
        fallback = [((b / 127.5) - 1.0) for b in digest[:IMAGE_FINGERPRINT_DIM]]
        norm = math.sqrt(sum(v * v for v in fallback)) or 1.0
        return [round(v / norm, 6) for v in fallback]

    blocks_8x4 = arr.reshape(4, 16, 8, 8).mean(axis=(1, 3)).flatten()
    ahash_vec = (blocks_8x4 - float(blocks_8x4.mean())).tolist()

    gx = arr[:, 2:] - arr[:, :-2]
    gy = arr[2:, :] - arr[:-2, :]
    gx_c, gy_c = gx[1:-1, :], gy[:, 1:-1]
    mag = np.hypot(gx_c, gy_c)
    ang = (np.arctan2(gy_c, gx_c) + np.pi) % (2.0 * np.pi)
    hist, _ = np.histogram(ang, bins=np.linspace(0.0, 2.0 * np.pi, 17), weights=mag)
    hist_vec = hist.astype(np.float32).tolist()

    pad_mag = np.zeros((64, 64), dtype=np.float32)
    pad_mag[1:-1, 1:-1] = mag
    spatial_grid = pad_mag.reshape(4, 16, 4, 16).mean(axis=(1, 3)).flatten().tolist()

    combined = ahash_vec + hist_vec + spatial_grid
    if len(combined) != IMAGE_FINGERPRINT_DIM:
        raise ValueError(f"Expected {IMAGE_FINGERPRINT_DIM}-dim fingerprint, got {len(combined)}")
    norm = math.sqrt(sum(x * x for x in combined))
    if norm <= 1e-12:
        return [0.0] * IMAGE_FINGERPRINT_DIM
    return [round(float(x) / norm, 6) for x in combined]


def _build_corpus_tf(rows: Sequence[Any], q_tokens: list[str]) -> tuple[list[dict[str, int]], dict[str, int]]:
    doc_tf_maps: list[dict[str, int]] = []
    df_counts: dict[str, int] = dict.fromkeys(set(q_tokens), 0)
    for r in rows:
        tf_map: dict[str, int] = {}
        for t in _tokenize(f"{r['title']} {r['content']}"):
            tf_map[t] = tf_map.get(t, 0) + 1
        doc_tf_maps.append(tf_map)
        for qt in df_counts:
            if qt in tf_map:
                df_counts[qt] += 1
    return doc_tf_maps, df_counts


def _bm25_doc_score(q_tokens: list[str], tf_map: dict[str, int], df_counts: dict[str, int], stats: tuple[int, int, float]) -> float:
    dl, n_docs, avgdl = stats
    k1, b = 1.5, 0.75
    score = 0.0
    for qt in q_tokens:
        tf = tf_map.get(qt, 0)
        if tf == 0:
            continue
        df = df_counts.get(qt, 0)
        idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
        score += idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (dl / avgdl))))
    return score


def fuse_hybrid_search(
    rows: Sequence[Any],
    query: str,
    q_emb: list[float],
    *,
    top_k: int = 5,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """Compute BM25 + vector cosine scores and merge via Reciprocal Rank Fusion."""
    q_tokens = _tokenize(query)
    n_docs = len(rows)
    avgdl = max(1.0, sum(int(r["token_count"]) for r in rows) / n_docs)
    doc_tf_maps, df_counts = _build_corpus_tf(rows, q_tokens)

    bm25_scores: list[tuple[int, float]] = []
    vec_scores: list[tuple[int, float]] = []
    for idx, r in enumerate(rows):
        dl = max(1, int(r["token_count"]))
        bm25_scores.append((idx, _bm25_doc_score(q_tokens, doc_tf_maps[idx], df_counts, (dl, n_docs, avgdl))))
        doc_vec = _unpack_vector(r["embedding_blob"])
        if len(doc_vec) != len(q_emb):
            doc_vec = deterministic_ngram_embedding(f"{r['title']} {r['content']}", dim=len(q_emb))
        vec_scores.append((idx, cosine_similarity(q_emb, doc_vec)))

    lex_rank = {doc_idx: rank for rank, (doc_idx, _) in enumerate(sorted(bm25_scores, key=lambda x: x[1], reverse=True), start=1)}
    vec_rank = {doc_idx: rank for rank, (doc_idx, _) in enumerate(sorted(vec_scores, key=lambda x: x[1], reverse=True), start=1)}
    bm25_val = dict(bm25_scores)
    vec_val = dict(vec_scores)

    fused: list[dict[str, Any]] = []
    for idx, r in enumerate(rows):
        r_lex, r_vec = lex_rank[idx], vec_rank[idx]
        rrf_score = (1.0 / (rrf_k + r_lex)) + (1.0 / (rrf_k + r_vec))
        fused.append({
            "doc_id": r["doc_id"],
            "title": r["title"],
            "content": r["content"],
            "metadata": json.loads(r["metadata_json"] or "{}"),
            "rrf_score": round(rrf_score, 6),
            "lexical_rank": r_lex,
            "vector_rank": r_vec,
            "bm25_score": round(bm25_val[idx], 5),
            "vector_score": round(vec_val[idx], 5),
        })

    fused.sort(key=lambda item: (item["rrf_score"], item["bm25_score"], item["vector_score"]), reverse=True)
    return fused[: max(1, int(top_k))]


def _extract_sentence_entities(sent: str, all_entities: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    sent_entities: list[tuple[str, str]] = []
    seen_in_sent: set[str] = set()
    for ent_type, pattern in _ENTITY_PATTERNS:
        for match in pattern.finditer(sent):
            raw_val = re.sub(r"\s+", " ", match.group(0).strip())
            norm_key = raw_val.lower()
            if norm_key not in seen_in_sent:
                seen_in_sent.add(norm_key)
                sent_entities.append((raw_val, ent_type))
                all_entities[norm_key] = (raw_val, ent_type)
    return sent_entities


def _make_triple(src: tuple[str, str], dst: tuple[str, str], doc_id: str, evidence: str) -> dict[str, str]:
    src_name, src_type = src
    dst_name, dst_type = dst
    return {
        "source": src_name,
        "source_type": src_type,
        "relation": _relation_for_pair(src_type, dst_type),
        "target": dst_name,
        "target_type": dst_type,
        "doc_id": doc_id,
        "evidence": evidence[:240],
    }


def extract_entities_and_triples(clean_doc_id: str, text: str) -> tuple[dict[str, tuple[str, str]], list[dict[str, str]]]:
    """Extract technical entities and directed triples from document text."""
    sentences = [s.strip() for s in re.split(r"[\n.;]+", text or "") if s.strip()]
    extracted_triples: list[dict[str, str]] = []
    all_entities: dict[str, tuple[str, str]] = {}

    for sent in sentences:
        sent_entities = _extract_sentence_entities(sent, all_entities)
        for i in range(len(sent_entities)):
            for j in range(i + 1, len(sent_entities)):
                extracted_triples.append(_make_triple(sent_entities[i], sent_entities[j], clean_doc_id, sent))

    ent_list = list(all_entities.values())
    if not extracted_triples and len(ent_list) >= 2:
        for i in range(len(ent_list) - 1):
            extracted_triples.append(_make_triple(ent_list[i], ent_list[i + 1], clean_doc_id, text or ""))

    return all_entities, extracted_triples


def _find_seed_nodes(edges: Sequence[Any], query: str) -> set[str]:
    q_lower = (query or "").lower()
    q_tokens = set(_tokenize(q_lower))
    all_nodes: set[str] = set()
    for e in edges:
        all_nodes.add(str(e["source_name"]))
        all_nodes.add(str(e["target_name"]))
    seeds: set[str] = set()
    for node in all_nodes:
        n_low = node.lower()
        if n_low in q_lower or (q_tokens & set(_tokenize(n_low))):
            seeds.add(n_low)
    return seeds


def traverse_knowledge_subgraph(edges: Sequence[Any], query: str, max_hops: int) -> list[dict[str, Any]]:
    """Breadth-first traversal up to ``max_hops`` over KG edge rows starting from query-matched seed nodes."""
    seed_nodes = _find_seed_nodes(edges, query)
    if not seed_nodes:
        return []

    visited_nodes: set[str] = set(seed_nodes)
    queue: deque[tuple[str, int]] = deque((n, 0) for n in seed_nodes)
    visited_edge_keys: set[tuple[str, str, str, str]] = set()
    subgraph: list[dict[str, Any]] = []

    while queue:
        curr_node_low, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for e in edges:
            src, dst = str(e["source_name"]), str(e["target_name"])
            src_low, dst_low = src.lower(), dst.lower()
            if curr_node_low not in (src_low, dst_low):
                continue
            edge_key = (src_low, str(e["relation"]), dst_low, str(e["doc_id"]))
            if edge_key not in visited_edge_keys:
                visited_edge_keys.add(edge_key)
                subgraph.append({
                    "source": src,
                    "source_type": str(e["source_type"]),
                    "relation": str(e["relation"]),
                    "target": dst,
                    "target_type": str(e["target_type"]),
                    "doc_id": str(e["doc_id"]),
                    "evidence": str(e["evidence"]),
                    "hop": depth + 1,
                })
            neighbor_low = dst_low if curr_node_low == src_low else src_low
            if neighbor_low not in visited_nodes:
                visited_nodes.add(neighbor_low)
                queue.append((neighbor_low, depth + 1))

    return subgraph


def _extract_numbers(text: str) -> list[str]:
    nums: list[str] = []
    for match in _NUM_CLAIM_RE.finditer(text or ""):
        token = match.group(0).replace(",", ".").replace(" ", "")
        if token and token not in nums:
            nums.append(token)
    return nums


def _build_doc_num_entries(retrieved_docs: list[dict[str, Any]]) -> list[tuple[str, str, set[str]]]:
    entries: list[tuple[str, str, set[str]]] = []
    for doc in retrieved_docs or []:
        title = str(doc.get("title") or doc.get("doc_id") or "Bilgi Bankası").strip()
        content = str(doc.get("content") or "")
        nums = set(_extract_numbers(f"{title} {content}"))
        expanded = set(nums)
        for n in list(nums):
            if "-" in n:
                expanded.update(part for part in n.split("-") if part)
            if n.startswith("±"):
                expanded.add(n[1:])
        entries.append((title, content, expanded))
    return entries


def _find_supporting_title(num: str, doc_entries: list[tuple[str, str, set[str]]]) -> str | None:
    clean_num = num.lstrip("±")
    for title, content, doc_num_set in doc_entries:
        if num in doc_num_set or clean_num in doc_num_set or num in content:
            return title
    return None


def _attach_citation_tags(clause: str, titles: list[str]) -> tuple[str, int]:
    updated = clause
    attached = 0
    for title in titles:
        tag = f"[Kaynak: {title}]"
        if tag in updated:
            continue
        if updated.endswith((".", "!", "?")):
            updated = f"{updated[:-1]} {tag}{updated[-1]}"
        else:
            updated = f"{updated} {tag}"
        attached += 1
    return updated, attached


def verify_citations(answer: str, retrieved_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify numerical claims in ``answer`` against ``retrieved_docs`` and attach ``[Kaynak: <doc_title>]``."""
    raw_answer = (answer or "").strip()
    if not raw_answer:
        return {
            "annotated_answer": "",
            "verified_claims": [],
            "unverified_claims": [],
            "grounding_ratio": 1.0,
            "citations_attached": 0,
        }

    doc_entries = _build_doc_num_entries(retrieved_docs)
    verified_claims: list[dict[str, str]] = []
    unverified_claims: list[str] = []
    citations_attached = 0
    annotated_clauses: list[str] = []

    for clause in re.split(r"(?<=[.!?])\s+|\n+", raw_answer):
        if not clause.strip():
            continue
        matched_titles: list[str] = []
        for num in _extract_numbers(clause):
            supporting_title = _find_supporting_title(num, doc_entries)
            if supporting_title is not None:
                verified_claims.append({"claim": num, "source": supporting_title})
                if supporting_title not in matched_titles:
                    matched_titles.append(supporting_title)
            elif num not in unverified_claims:
                unverified_claims.append(num)
        updated_clause, added = _attach_citation_tags(clause, matched_titles)
        citations_attached += added
        annotated_clauses.append(updated_clause)

    total_claims = len(verified_claims) + len(unverified_claims)
    grounding_ratio = 1.0 if total_claims == 0 else round(len(verified_claims) / total_claims, 4)
    return {
        "annotated_answer": " ".join(annotated_clauses),
        "verified_claims": verified_claims,
        "unverified_claims": unverified_claims,
        "grounding_ratio": grounding_ratio,
        "citations_attached": citations_attached,
    }
