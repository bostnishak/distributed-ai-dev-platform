"""Cluster A Unit Tests: 4-Layer Cognitive Memory, ReAct Deterministic Tools, and PPTX/Deep Research."""

from __future__ import annotations

from pathlib import Path

import pytest

import config
import deep_research as dr
import memory_engine as mem
import tool_executor as te

pytestmark = pytest.mark.integration


def test_four_layer_cognitive_memory(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    mem.init_memory_db()

    mem.record_conversation_turn(
        conversation_id="conv-101",
        user_text="Benim adım İshak, CNC projelerinde ISO 2768-mK ve AISI 4140 kullanıyoruz, arayüzde emoji istemiyorum.",
        assistant_text="Anlaşıldı, ISO 2768-mK ve AISI 4140 kurallarını kaydettim.",
        model_used="qwen3.5:9b",
        task_type="genel",
    )

    facts = mem.list_semantic_facts()
    assert len(facts) >= 2
    ctx_block = mem.build_memory_context_block("CNC tolerans")
    assert "ISO 2768-mK" in ctx_block or "AISI 4140" in ctx_block

    hits = mem.search_episodic_memory("ISO")
    assert len(hits) >= 1

    # Context compaction
    long_msgs = [{"role": "system", "content": "Sistem"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Mesaj {i} " * 40}
        for i in range(12)
    ]
    compacted = mem.compact_conversation_context(long_msgs, max_chars=800)
    assert len(compacted) < len(long_msgs)


def test_deterministic_math_units_and_sql_tools():
    q = te.solve_quadratic_or_linear(1.0, -5.0, 6.0)
    assert q["roots"] == [2.0, 3.0]

    lin = te.solve_linear_system([[2.0, 1.0], [1.0, 3.0]], [5.0, 10.0])
    assert lin["solution"] == [1.0, 3.0]

    st = te.compute_descriptive_stats([10.0, 20.0, 30.0, 40.0, 50.0])
    assert st["mean"] == 30.0
    assert st["median"] == 30.0

    conv = te.convert_engineering_units(25.4, "mm", "inch")
    assert conv["result"] == 1.0

    cnc_calc = te.calculate_spindle_rpm_and_feed(180.0, 50.0, 0.15, teeth=1)
    assert cnc_calc["rpm"] > 1100

    csv_sample = "kategori,adet,fiyat\nCNC,10,1500\nTakim,5,800\nCNC,4,2000"
    sql_res = te.query_csv_with_sql(csv_sample, "SELECT kategori, SUM(adet) AS toplam_adet FROM data GROUP BY kategori ORDER BY toplam_adet DESC")
    assert sql_res["rows"][0] == ["CNC", 14]


def test_deep_research_and_pptx_generator(tmp_path: Path):
    qs = dr.decompose_research_questions("Dağıtık Yapay Zekâ Sistemleri")
    assert len(qs) == 4

    out_pptx = tmp_path / "test_sunum.pptx"
    dr.build_pptx_presentation(
        title="Kurumsal Yapay Zekâ Stratejisi",
        subtitle="2026 Yol Haritası",
        slides=[
            {"title": "1. Mimari Vizyon", "bullets": ["%100 Yerel Çıkarım", "Çoklu Ajan Konseyi"]},
            {"title": "2. Finansal Etki", "bullets": ["%40 Zaman Tasarrufu", "Sıfır Bulut Maliyeti"]},
        ],
        out_path=out_pptx,
    )
    assert out_pptx.is_file()
    assert out_pptx.stat().st_size > 1500
