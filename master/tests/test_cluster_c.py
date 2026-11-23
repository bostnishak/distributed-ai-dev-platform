"""Unit tests for Cluster C:
- ``master/cluster_telemetry.py`` ([M35]..[M38])
- ``master/hybrid_graph_rag.py`` ([M39]..[M42])
- ``master/llmops_pipeline.py`` ([M43]..[M45])
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

import cluster_telemetry
import config
import hybrid_graph_rag
import llmops_pipeline


def _make_drawing_png(kind: str) -> bytes:
    """Create a synthetic 128x128 technical drawing PNG in memory."""
    img = Image.new("L", (128, 128), color=255)
    draw = ImageDraw.Draw(img)
    if kind == "flange_a":
        draw.ellipse((20, 20, 108, 108), outline=0, width=3)
        draw.ellipse((48, 48, 80, 80), outline=0, width=2)
        draw.line((10, 64, 118, 64), fill=0, width=1)
        draw.line((64, 10, 64, 118), fill=0, width=1)
    elif kind == "flange_b":
        # Nearly identical circular flange with slight offset
        draw.ellipse((21, 21, 107, 107), outline=0, width=3)
        draw.ellipse((47, 47, 81, 81), outline=0, width=2)
        draw.line((12, 64, 116, 64), fill=0, width=1)
        draw.line((64, 12, 64, 116), fill=0, width=1)
    else:
        # Step shaft rectangle geometry
        draw.rectangle((12, 46, 60, 82), outline=0, width=3)
        draw.rectangle((60, 34, 116, 94), outline=0, width=3)
        draw.line((8, 16, 120, 16), fill=0, width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_thompson_bandit_router_convergence_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    router = cluster_telemetry.ThompsonBanditRouter(seed=42)

    for _ in range(12):
        router.record_outcome("kod_python", "qwen2.5-coder:7b", success=True, latency_ms=420.0)
        router.record_outcome("kod_python", "llama3.2:3b", success=False, latency_ms=950.0)

    choice = router.select_best_candidate(
        "kod_python",
        candidates=["llama3.2:3b", "qwen2.5-coder:7b"],
        deterministic=True,
    )
    assert choice["selected"] == "qwen2.5-coder:7b"
    assert choice["posterior_mean"] > 0.85

    # Reload from persisted JSON state file and confirm parameters survived
    reloaded = cluster_telemetry.ThompsonBanditRouter(seed=42)
    stats = reloaded.get_arm_stats("kod_python", "qwen2.5-coder:7b")
    assert stats["trials"] == 12.0
    assert stats["successes"] == 12.0
    assert (tmp_path / "bandit_state.json").exists()


def test_thompson_bandit_warm_cache_affinity_bonus(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    router = cluster_telemetry.ThompsonBanditRouter(warm_affinity_bonus=0.20, seed=7)

    # Both models have identical prior Beta(1, 1); warm model must win deterministically
    res = router.select_best_candidate(
        "analiz",
        candidates=["qwen3.5:9b", "gemma4:e4b"],
        warm_models={"gemma4:e4b"},
        deterministic=True,
    )
    assert res["selected"] == "gemma4:e4b"
    assert res["is_warm"] is True
    assert res["utility"] > res["rankings"][1]["utility"]


def test_local_hardware_telemetry_and_task_checkpointing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    telemetry = cluster_telemetry.get_local_hardware_telemetry(query_ollama=False)
    assert telemetry["ram_total_gb"] > 0.0
    assert telemetry["ram_free_gb"] >= 0.0
    assert telemetry["process_rss_mb"] > 0.0
    assert isinstance(telemetry["warm_models"], list)

    saved = cluster_telemetry.save_task_checkpoint(
        task_id="swarm-job-101",
        step=3,
        state={"completed_files": ["db.py", "api.py"], "assigned_agent": "node-2"},
    )
    assert saved["step"] == 3

    loaded = cluster_telemetry.load_task_checkpoint("swarm-job-101")
    assert loaded is not None
    assert loaded["step"] == 3
    assert loaded["state"]["assigned_agent"] == "node-2"
    assert cluster_telemetry.load_task_checkpoint("non-existent-task") is None


def test_hybrid_graph_rag_rrf_ranking(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    rag = hybrid_graph_rag.HybridGraphRAG(db_path=tmp_path / "graph_rag.db")

    rag.add_document(
        doc_id="doc-iso286",
        title="ISO 286 H7 Delik Tolerans ve Rayba Tablosu",
        content="Ø42 H7 delik toleransı +0.025 / 0.000 mm olup OP20 operasyonunda karbür rayba ile işlenir.",
        metadata={"rev": "R4"},
    )
    rag.add_document(
        doc_id="doc-cutting",
        title="AISI 4140 Kesme Hızı Parametreleri",
        content="AISI 4140 ıslah çeliği tornalama operasyonunda Vc 180 m/dk ve TiAlN uç kullanılır.",
        metadata={"rev": "R2"},
    )
    rag.add_document(
        doc_id="doc-as9102",
        title="AS9102 FAI Kalite Kontrol",
        content="Kritik ölçülerde CMM cihazı ile %100 kontrol ve Cpk >= 1.33 şartı uygulanır.",
        metadata={"rev": "R1"},
    )

    hits = rag.search("Ø42 H7 delik toleransı karbür rayba", top_k=2)
    assert len(hits) == 2
    assert hits[0]["doc_id"] == "doc-iso286"
    expected_rrf = round(
        (1.0 / (60 + hits[0]["lexical_rank"])) + (1.0 / (60 + hits[0]["vector_rank"])),
        6,
    )
    assert hits[0]["rrf_score"] == expected_rrf


def test_knowledge_graph_extraction_and_two_hop_bfs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    triples = hybrid_graph_rag.extract_and_store_triples(
        doc_id="spec-4140",
        text=(
            "AISI 4140 malzemede H7 toleransı işlenir. "
            "H7 toleransı OP20 operasyonunda karbür rayba ve ISO 286 standardı ile doğrulanır."
        ),
    )
    assert len(triples) >= 2

    subgraph = hybrid_graph_rag.query_knowledge_subgraph("AISI 4140", hops=2)
    assert len(subgraph) >= 2
    hops_found = {edge["hop"] for edge in subgraph}
    assert 1 in hops_found
    assert 2 in hops_found
    nodes = {edge["source"] for edge in subgraph} | {edge["target"] for edge in subgraph}
    assert any("4140" in n for n in nodes)
    assert any("H7" in n for n in nodes)


def test_vision_rag_drawing_fingerprint_similarity(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    rag = hybrid_graph_rag.HybridGraphRAG(db_path=tmp_path / "graph_rag.db")

    flange_a = _make_drawing_png("flange_a")
    flange_b = _make_drawing_png("flange_b")
    shaft = _make_drawing_png("shaft")

    fp_a = hybrid_graph_rag.compute_image_fingerprint(flange_a)
    assert len(fp_a) == 64

    rag.index_drawing("DRW-FLANGE-01", "Flanş Rev A", flange_a, metadata={"cycle_min": 14.5})
    rag.index_drawing("DRW-SHAFT-02", "Kademeli Mil", shaft, metadata={"cycle_min": 9.0})

    similar = hybrid_graph_rag.find_similar_drawings(flange_b, top_k=2)
    assert len(similar) == 2
    assert similar[0]["drawing_id"] == "DRW-FLANGE-01"
    assert similar[0]["similarity"] > similar[1]["similarity"]


def test_citation_guardrail_verifies_numbers_and_attaches_sources():
    docs = [
        {
            "doc_id": "iso-286",
            "title": "ISO 286 Geçme Tablosu",
            "content": "Ø42 H7 delik için üst sapma 0.025 mm ve Cpk >= 1.33 olarak uygulanır.",
        },
        {
            "doc_id": "speeds",
            "title": "Kesme Hızı Rehberi",
            "content": "AISI 4140 tornalama kesme hızı 180 m/dk değerindedir.",
        },
    ]
    answer = "Ø42 H7 delik toleransı 0.025 mm düzeyindedir. Kesme hızı 180 m/dk seçilmelidir."
    res = hybrid_graph_rag.verify_citations(answer, docs)

    assert "[Kaynak: ISO 286 Geçme Tablosu]" in res["annotated_answer"]
    assert "[Kaynak: Kesme Hızı Rehberi]" in res["annotated_answer"]
    assert res["grounding_ratio"] == 1.0
    assert len(res["unverified_claims"]) == 0
    assert res["citations_attached"] >= 2


def test_llmops_dpo_collection_and_model_promotion_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    rec1 = llmops_pipeline.record_dpo_preference(
        prompt="AISI 4140 Vc kaç m/dk olmalı?",
        chosen="AISI 4140 için tornalamada Vc = 160-210 m/dk aralığındadır.",
        rejected="Her malzemede 900 m/dk kullanılır.",
        domain="cnc",
    )
    rec2 = llmops_pipeline.record_dpo_preference(
        prompt="FastAPI health endpoint yaz.",
        chosen="@app.get('/health')\ndef health(): return {'status': 'ok'}",
        rejected="print('ok')",
        domain="coding",
    )
    assert rec1["id"] != rec2["id"]

    stats = llmops_pipeline.get_llmops_stats(min_pairs_threshold=2)
    assert stats["total_pairs"] == 2
    assert stats["by_domain"] == {"cnc": 1, "coding": 1}
    assert stats["ready_for_nightly_qlora"] is True

    # Candidate strictly outperforms baseline across golden test suite
    baseline = [0.72, 0.75, 0.70, 0.74, 0.73, 0.71, 0.76, 0.72]
    candidate = [0.84, 0.86, 0.82, 0.85, 0.83, 0.84, 0.88, 0.85]
    gate_pass = llmops_pipeline.evaluate_model_gate(baseline, candidate)
    assert gate_pass["promote"] is True
    assert gate_pass["delta"] > 0.10
    assert gate_pass["p_value_approx"] < 0.01

    # Regressed candidate must be blocked from promotion
    regressed = [0.68, 0.70, 0.69, 0.71, 0.67, 0.70, 0.71, 0.69]
    gate_fail = llmops_pipeline.evaluate_model_gate(baseline, regressed)
    assert gate_fail["promote"] is False
    assert gate_fail["delta"] < 0.0
