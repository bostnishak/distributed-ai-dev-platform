"""Wave 3B Verification Suite: EPK-01 (Web Archive/Robots), EPK-02 (Turkish Eval/Kappa), EPK-07 (Numeric/Unit Verify), EPK-14 (Advanced RAG), EPK-15 (Memory Conflicts)."""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi.testclient import TestClient

import app as master_app
import eval_studio
import memory_conflicts
from hallucination import numeric_check
from rag import advanced as rag_advanced

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_epk01_web_archive_robots_ssrf_and_offline_citations():
    """EPK-01 (PKA-01..10, ARS-01/04, SOH-06/07): Robots compliance, SSRF block, deduplication & offline search."""
    client = TestClient(master_app.app)

    # Robots.txt check
    robots = "User-agent: *\nDisallow: /admin\nAllow: /admin/public\n"
    assert client.post("/api/rag/web/robots-check", json={"robots_txt": robots, "path": "/admin/secret"}).json()["allowed"] is False
    assert client.post("/api/rag/web/robots-check", json={"robots_txt": robots, "path": "/admin/public/info"}).json()["allowed"] is True

    # SSRF private IP must be rejected
    r_ssrf = client.post("/api/rag/web/archive", json={"url": "http://127.0.0.1:8000/secret", "title": "bad", "content": "secret"})
    assert r_ssrf.status_code == 400

    # Public archive + deduplication + cited offline search
    slug = secrets.token_hex(4)
    r_arch = client.post(
        "/api/rag/web/archive",
        json={
            "url": f"https://example.org/docs/{slug}",
            "title": f"Kuantum Şifreleme Kılavuzu {slug}",
            "content": f"NIST post-kuantum ML-KEM standardı {slug} yerel sistemlerde 256 bit güvenlik sağlar.",
        },
    )
    assert r_arch.status_code == 200, r_arch.text
    assert r_arch.json()["credibility_score"] >= 0.85

    r_search = client.post("/api/rag/web/archive/search", json={"query": f"ML-KEM {slug}", "limit": 3})
    assert r_search.status_code == 200
    body = r_search.json()
    assert body["offline_mode"] is True
    assert body["count"] >= 1
    assert body["results"][0]["citation"] == "S1"


def test_epk02_turkish_eval_datasets_annotation_and_cohens_kappa():
    """EPK-02 (PKA-11..20, OPR-04): 300-sample Turkish dataset, annotation persistence & exact Cohen's kappa."""
    ds_path = REPO_ROOT / "eval" / "datasets" / "turkish_benchmark_v1.jsonl"
    assert ds_path.is_file()
    rows = eval_studio.load_jsonl_dataset("eval/datasets/turkish_benchmark_v1.jsonl")
    assert len(rows) >= 300
    assert {r["domain"] for r in rows} == {"factuality", "citation", "nli", "intent", "vqa_meta", "asr_norm"}

    client = TestClient(master_app.app)
    r_ds = client.get("/api/eval-studio/datasets")
    assert r_ds.status_code == 200
    assert any(d["dataset_id"] == "turkish_benchmark_v1" for d in r_ds.json()["datasets"])

    ds_id = f"tr_kappa_{secrets.token_hex(3)}"
    pairs = [("i1", "yes", "yes"), ("i2", "yes", "yes"), ("i3", "no", "no"), ("i4", "no", "no"), ("i5", "yes", "no")]
    for iid, la, lb in pairs:
        assert client.post("/api/eval-studio/annotate", json={"dataset_id": ds_id, "item_id": iid, "annotator_id": "a1", "label": la}).status_code == 200
        assert client.post("/api/eval-studio/annotate", json={"dataset_id": ds_id, "item_id": iid, "annotator_id": "a2", "label": lb}).status_code == 200

    r_kap = client.post("/api/eval-studio/kappa", json={"dataset_id": ds_id, "annotator_a": "a1", "annotator_b": "a2"})
    assert r_kap.status_code == 200
    assert r_kap.json()["observed_agreement"] == 0.8
    assert r_kap.json()["kappa"] >= 0.58

    # Fault injection: mismatched lengths rejected
    assert client.post("/api/eval-studio/kappa", json={"labels_a": ["a"], "labels_b": ["a", "b"]}).status_code == 400


def test_epk07_numeric_unit_consistency_and_sentence_citations():
    """EPK-07 (PKA-61..70): Unit-normalized numeric verification (1 km == 1000 m) & hallucinated number catch."""
    client = TestClient(master_app.app)
    sources = [{"id": "S1", "text": "Test pisti uzunluğu 1 km ve ağırlık sınırı 2.5 kg olarak belirlendi."}]

    # Equivalent units pass
    r_ok = client.post(
        "/api/hallucination/numeric-verify",
        json={"answer": "Pist uzunluğu 1000 m ve sınır 2500 g değerindedir [S1].", "sources": sources},
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["passed"] is True
    assert r_ok.json()["numeric_consistency"] == 1.0

    # Fabricated number fails
    r_bad = client.post(
        "/api/hallucination/numeric-verify",
        json={"answer": "Pist uzunluğu 9500 m olarak ölçüldü.", "sources": sources},
    )
    assert r_bad.status_code == 200
    assert r_bad.json()["passed"] is False
    assert "9500 m" in r_bad.json()["sentences"][0]["unsupported_numbers"]
    assert numeric_check.extract_normalized_quantities("2 gb")[0]["canonical"] == 2048.0


def test_epk14_parent_child_chunking_query_rewrite_rerank_and_ndcg():
    """EPK-14 (PKB-32..41): Parent-child hierarchy, Turkish query rewrite, cross-reranking & nDCG@5."""
    client = TestClient(master_app.app)
    long_doc = ("CNC tezgahında AISI 4140 çelik işleme parametreleri ve kesme hızı kılavuzu. " * 30).strip()

    r_pc = client.post("/api/rag/advanced/parent-child", json={"text": long_doc, "parent_size": 500, "child_size": 150})
    assert r_pc.status_code == 200
    pc = r_pc.json()
    assert pc["parent_count"] >= 3
    assert pc["child_count"] > pc["parent_count"]

    passages = [
        {"id": "d1", "content": "Hava durumu bugün güneşli ve sıcak."},
        {"id": "d2", "content": "RBAC yetki matrisi güvenlik hatası ve rol denetimi çözümü."},
        {"id": "d3", "content": "Genel yetki notları."},
    ]
    r_rr = client.post("/api/rag/advanced/rerank", json={"query": "güvenlik yetki hatası", "passages": passages, "top_k": 2})
    assert r_rr.status_code == 200
    rr = r_rr.json()
    assert len(rr["query_variants"]) >= 2
    assert rr["results"][0]["id"] == "d2"
    assert rag_advanced.compute_ndcg_at_k([3.0, 2.0, 1.0, 0.0], k=4) == 1.0


def test_epk15_memory_contradiction_queue_resolution_and_decay():
    """EPK-15 (PKB-42..51): Memory conflict detection, user resolution, and half-life decay consolidation."""
    client = TestClient(master_app.app)
    uid = f"mem_{secrets.token_hex(4)}"

    # First fact inserts cleanly without conflict
    r1 = client.post("/api/memory/conflicts/detect", json={"user_id": uid, "category": "preference", "fact_key": "editor", "candidate_value": "VSCode"})
    assert r1.status_code == 200 and r1.json()["conflict_detected"] is False

    # Contradictory fact queues a conflict
    r2 = client.post("/api/memory/conflicts/detect", json={"user_id": uid, "category": "preference", "fact_key": "editor", "candidate_value": "Neovim"})
    assert r2.status_code == 200 and r2.json()["conflict_detected"] is True
    cid = r2.json()["conflict_id"]

    # Conflict appears in open list
    r_list = client.get("/api/memory/conflicts", params={"user_id": uid, "status": "open"})
    assert r_list.status_code == 200
    assert any(c["id"] == cid for c in r_list.json()["conflicts"])

    # Resolve with merge
    r_res = client.post(f"/api/memory/conflicts/{cid}/resolve", json={"decision": "merge", "user_id": uid})
    assert r_res.status_code == 200
    assert "VSCode | Neovim" == r_res.json()["resolved_value"]

    # Consolidation & decay monotonicity
    r_con = client.post("/api/memory/consolidate", json={"user_id": uid, "half_life_days": 90.0})
    assert r_con.status_code == 200 and r_con.json()["memory_count"] >= 1
    assert memory_conflicts.score_memory_with_decay(1.0, 0.0, 90.0) == 1.0
    assert abs(memory_conflicts.score_memory_with_decay(1.0, 90.0, 90.0) - 0.5) < 0.01
