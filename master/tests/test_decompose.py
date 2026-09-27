import asyncio
import json

import pytest

import config
import decompose
from decompose import (
    AnalysisError,
    Endpoint,
    Entity,
    EntityField,
    Page,
    analyze_document,
    build_task_plan,
    context_window_for,
    merge_specs,
    split_into_chunks,
)
from spec_factory import make_spec


def run(coro):
    return asyncio.run(coro)


class TestChunking:
    def test_short_text_is_one_chunk(self):
        assert split_into_chunks("kısa metin", 100) == ["kısa metin"]

    def test_long_text_splits_on_paragraphs_within_limit(self):
        paragraphs = [f"## Bölüm {i}\n" + ("gereksinim " * 20).strip() for i in range(30)]
        text = "\n\n".join(paragraphs)
        chunks = split_into_chunks(text, 600)
        assert len(chunks) > 1
        assert all(len(c) <= 600 for c in chunks)
        # Nothing is lost and paragraph order is kept.
        assert "\n\n".join(chunks) == text

    def test_oversized_paragraph_is_cut(self):
        chunks = split_into_chunks("x" * 2500, 1000)
        assert [len(c) for c in chunks] == [1000, 1000, 500]


class TestContextWindow:
    def test_minimum_window(self, monkeypatch):
        monkeypatch.setattr(config, "NUM_PREDICT", 2048)
        assert context_window_for(100) == 8192

    def test_power_of_two_growth_and_cap(self, monkeypatch):
        monkeypatch.setattr(config, "NUM_PREDICT", 6144)
        monkeypatch.setattr(config, "NUM_CTX_MAX", 32768)
        assert context_window_for(5000) == 16384
        assert context_window_for(100_000) == 32768


class TestMerge:
    def test_merges_entities_endpoints_pages_across_chunks(self):
        a = make_spec()
        b = make_spec(
            project_name="",
            entities=[Entity(name="kitap", description="", fields=[
                EntityField(name="Baslik", type="string", required=True),
                EntityField(name="yazar", type="string", required=False),
            ])],
            api_endpoints=[
                Endpoint(method="GET", path="/api/kitaplar/", description="dup", entity="Kitap"),
                Endpoint(method="DELETE", path="api/kitaplar/{id}", description="Sil", entity="Kitap"),
            ],
            pages=[Page(name="Kitap Listesi", description="", entities=["Yazar"])],
            open_questions=["Bir üye aynı anda kaç kitap alabilir?", "Ceza var mı?"],
        )
        merged = merge_specs([a, b])
        kitap = next(e for e in merged.entities if e.name == "Kitap")
        assert [f.name for f in kitap.fields] == ["baslik", "isbn", "yazar"]
        paths = [(e.method, e.path) for e in merged.api_endpoints]
        assert ("GET", "/api/kitaplar") in paths
        assert ("DELETE", "/api/kitaplar/{id}") in paths
        assert len([p for p in paths if p[0] == "GET" and p[1].startswith("/api/kitaplar")]) == 1
        page = next(p for p in merged.pages if p.name == "Kitap listesi")
        assert page.entities == ["Kitap", "Yazar"]
        assert merged.open_questions == ["Bir üye aynı anda kaç kitap alabilir?", "Ceza var mı?"]
        assert merged.project_name == "Kütüphane Yönetim Sistemi"

    def test_drops_empty_names(self):
        spec = make_spec(entities=[Entity(name="  ", description="x", fields=[])], pages=[])
        assert merge_specs([spec]).entities == []


class TestTaskPlan:
    def test_graph_is_acyclic_and_ordered(self):
        tasks = build_task_plan(make_spec())
        keys = [t["key"] for t in tasks]
        assert len(keys) == len(set(keys))
        position = {k: i for i, k in enumerate(keys)}
        for task in tasks:
            for dep in task["depends_on"]:
                assert position[dep] < position[task["key"]]
                stage_of_dep = next(t["stage"] for t in tasks if t["key"] == dep)
                assert stage_of_dep < task["stage"]

    def test_expected_pipeline(self):
        tasks = build_task_plan(make_spec())
        types = [t["type"] for t in tasks]
        assert types[0] == "requirements"
        assert tasks[0]["status"] == "done" and tasks[0]["performed_by"] == "master"
        assert all(t["status"] == "planned" for t in tasks[1:])
        assert types.count("database") == 1
        # 3 entities in groups of 2 -> 2 backend tasks, plus one for the unmatched /api/rapor.
        assert types.count("backend") == 3
        # 3 pages in groups of 2 -> 2 frontend tasks.
        assert types.count("frontend") == 2
        assert types[-4:] == ["testing", "review", "integration", "documentation"]
        by_type = {t["type"]: t for t in tasks}
        assert by_type["integration"]["stage"] == by_type["testing"]["stage"] + 1
        assert by_type["documentation"]["stage"] == by_type["integration"]["stage"] + 1

    def test_endpoints_matched_by_entity_name_or_path(self):
        tasks = build_task_plan(make_spec())
        backend = [t for t in tasks if t["type"] == "backend"]
        first = {ep["path"] for ep in backend[0]["details"]["endpoints"]}
        # "/api/uyeler" has no entity field but its path belongs to "Üye".
        assert first == {"/api/kitaplar", "/api/uyeler"}
        assert {ep["path"] for ep in backend[1]["details"]["endpoints"]} == {"/api/odunc"}
        assert backend[2]["title"] == "Backend API: diğer uç noktalar"
        assert {ep["path"] for ep in backend[2]["details"]["endpoints"]} == {"/api/rapor"}

    def test_frontend_depends_only_on_analysis(self):
        tasks = build_task_plan(make_spec())
        for task in tasks:
            if task["type"] == "frontend":
                assert task["depends_on"] == ["T1"]

    def test_empty_spec_still_yields_full_pipeline(self):
        empty = make_spec(entities=[], api_endpoints=[], pages=[], open_questions=[])
        types = [t["type"] for t in build_task_plan(empty)]
        assert types == [
            "requirements", "database", "backend", "frontend",
            "testing", "review", "integration", "documentation",
        ]


class TestAnalyzeDocument:
    def test_valid_answer(self):
        calls = []

        async def chat(system, user, schema, num_ctx):
            calls.append(num_ctx)
            assert "open_questions" in json.dumps(schema)
            return make_spec().model_dump_json()

        result = run(analyze_document("Kütüphane sistemi gereksinimleri...", chat))
        assert result.chunk_count == 1
        assert result.spec.project_name == "Kütüphane Yönetim Sistemi"
        assert calls == [8192]

    def test_retries_once_after_invalid_json(self):
        answers = iter(["{not json", make_spec().model_dump_json()])
        prompts = []

        async def chat(system, user, schema, num_ctx):
            prompts.append(user)
            return next(answers)

        result = run(analyze_document("doküman", chat))
        assert result.spec.entities
        assert "did not match the required JSON schema" in prompts[1]

    def test_fails_after_two_invalid_answers(self):
        async def chat(system, user, schema, num_ctx):
            return '{"project_name": "x"}'

        with pytest.raises(AnalysisError):
            run(analyze_document("doküman", chat))

    def test_empty_document_is_rejected(self):
        async def chat(*_args):
            raise AssertionError("model must not be called")

        with pytest.raises(AnalysisError):
            run(analyze_document("  \n\n ", chat))

    def test_long_document_is_analyzed_in_chunks_and_merged(self, monkeypatch):
        monkeypatch.setattr(decompose, "max_chunk_chars", lambda: 500)
        text = "\n\n".join(f"Bölüm {i}: " + "ayrıntı " * 40 for i in range(6))
        systems = []

        async def chat(system, user, schema, num_ctx):
            systems.append(system)
            index = len(systems)
            return make_spec(
                entities=[Entity(name=f"Varlik{index}", description="", fields=[])],
                open_questions=[f"Soru {index}"],
            ).model_dump_json()

        result = run(analyze_document(text, chat))
        assert result.chunk_count == len(systems) > 1
        assert all("part" in s for s in systems)
        assert [e.name for e in result.spec.entities] == [f"Varlik{i}" for i in range(1, len(systems) + 1)]
        assert len(result.spec.open_questions) == len(systems)
