"""Comprehensive test suite for Parca 2: GW-01..GW-20, ORC-01..ORC-24, MODE-01..MODE-08 (including 60 E2E scenarios)."""

from __future__ import annotations

import ast
import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import app as master_app
import db
from gateway.client import (
    DECODING_PROFILES,
    BudgetExceededError,
    CancellationToken,
    CircuitBreaker,
    ConnectionFailedError,
    LLMClient,
    ModelNotFoundError,
    classify_error,
    get_run_traces,
)
from gateway.prompts import build_layered_system_prompt, is_simple_greeting, load_template
from gateway.providers import AgentProvider, ProviderResponse, load_optional_cloud_providers
from gateway.registry import (
    choose_dynamic_num_ctx,
    estimate_tokens,
    fit_messages_to_context,
    list_models,
    plan_context_strategy,
    select_model,
    sync_from_ollama,
)
from orchestrator.classifier import (
    classify_intent,
    decompose_multi_intent,
    detect_language,
    load_intent_catalog,
)
from orchestrator.contracts import (
    build_contract,
    enforce_contract,
    parse_format_directives,
    validate_contract,
)
from orchestrator.pipeline import run_pipeline
from orchestrator.planner import (
    DAGExecutor,
    ExecutionPlan,
    PlanStep,
    PlanValidationError,
    validate_plan,
)
from orchestrator.state import (
    SSE_EVENT_TYPES,
    apply_targeted_edit,
    check_clarification_needed,
    create_job,
    feedback_summary,
    filter_relevant_memories,
    get_artifact,
    get_job,
    get_run,
    load_conversation_state,
    make_sse_event,
    record_feedback,
    save_artifact,
    update_job,
)
from orchestrator.tools_registry import build_default_registry, run_react_loop

MASTER_DIR = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- Fake Provider for Deterministic Tests

class FakeProvider:
    name = "fake"
    is_cloud = False

    def __init__(self, responses: list[str] | None = None, fail_models: set[str] | None = None) -> None:
        self.responses = list(responses or ["Merhaba, nasıl yardımcı olabilirim?"])
        self.fail_models = set(fail_models or set())
        self.calls: list[dict[str, Any]] = []

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        *,
        format_schema: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        timeout_s: float = 120.0,
    ) -> ProviderResponse:
        self.calls.append({"model": model, "messages": messages, "options": options, "tools": tools})
        if model in self.fail_models:
            raise RuntimeError(f"404 model not found: {model}")
        idx = min(len(self.calls) - 1, len(self.responses) - 1)
        text = self.responses[idx]
        return ProviderResponse(
            content=text,
            model=model,
            provider=self.name,
            tokens_in=25,
            tokens_out=max(5, len(text.split())),
            latency_ms=4,
            node_id="fake-node",
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        options: dict[str, Any],
        *,
        timeout_s: float = 180.0,
    ) -> AsyncIterator[dict[str, Any]]:
        res = await self.chat(model, messages, options, timeout_s=timeout_s)
        for tok in res.content.split(" "):
            yield {"type": "token", "content": tok + " "}
        yield {"type": "done", "model": model, "provider": self.name, "tokens_in": 20, "tokens_out": 10}

    async def embed(self, model: str, text: str, timeout_s: float = 30.0) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]


# ---------------------------------------------------------------- GW-01..GW-20 Tests

def test_gw01_no_direct_ollama_calls_outside_gateway():
    """GW-01: No master/*.py file outside master/gateway/ may directly call /api/chat|generate|embed."""
    pattern = re.compile(r"/api/(?:chat|generate|embed|embeddings)")
    offenders: list[str] = []
    for py_file in sorted(MASTER_DIR.glob("*.py")):
        txt = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(txt.splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{py_file.name}:{lineno}: {line.strip()}")
    assert offenders == [], f"Direct Ollama API calls found outside master/gateway/: {offenders}"


def test_gw02_cloud_providers_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_CLOUD_PROVIDERS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-should-not-load")
    loaded = load_optional_cloud_providers()
    assert loaded == {}


@pytest.mark.anyio
async def test_gw02_agent_provider_end_to_end():
    """GW-02: AgentProvider dispatches task to db.tasks and resolves when worker finishes it."""
    db.init_db()
    prov = AgentProvider(poll_interval_s=0.05)

    async def _complete_soon():
        await asyncio.sleep(0.1)
        with db.connect() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'done', result = ? WHERE key = 'GW1' AND status != 'done'",
                ("Ajan tarafından üretilen yanıt.",),
            )

    worker = asyncio.create_task(_complete_soon())
    try:
        res = await prov.chat(
            "qwen3.5:9b",
            [{"role": "user", "content": "Merhaba ajan"}],
            {},
            timeout_s=3.0,
        )
        assert "Ajan tarafından üretilen yanıt" in res.content
        assert res.provider == "agent"
    finally:
        await worker


@pytest.mark.anyio
async def test_gw03_gw04_registry_sync_and_explainable_selection():
    """GW-03 & GW-04: Mock Ollama sync populates capabilities and select_model returns explanation."""

    class _MockOllama:
        async def list_tags(self):
            return [
                {"name": "qwen2.5-coder:7b", "size": 4_500_000_000, "details": {"parameter_size": "7B", "quantization_level": "Q4_K_M"}},
                {"name": "qwen3.5:9b", "size": 6_000_000_000, "details": {"parameter_size": "9B", "quantization_level": "Q4_K_M"}},
            ]

        async def show_model(self, name: str):
            return {"model_info": {"qwen.context_length": 32768}, "capabilities": ["completion", "tools"]}

        async def list_running(self):
            return [{"name": "qwen2.5-coder:7b"}]

    synced = await sync_from_ollama(_MockOllama())
    assert len(synced) >= 2
    models = {m["name"]: m for m in list_models()}
    assert "qwen2.5-coder:7b" in models
    assert models["qwen2.5-coder:7b"]["warm"] is True

    sel = select_model(task_type="kod", required_ctx=4096)
    assert sel.model
    assert sel.score > 0
    assert sel.reason
    assert sel.ctx_max >= 4096


def test_gw05_gw06_gw10_context_and_dynamic_num_ctx():
    assert choose_dynamic_num_ctx(1500, 32768) == 4096
    assert choose_dynamic_num_ctx(4500, 32768) == 8192
    assert choose_dynamic_num_ctx(10000, 32768) == 16384
    assert choose_dynamic_num_ctx(22000, 32768) == 32768
    assert plan_context_strategy(500, 8192)["strategy"] == "direct"
    assert plan_context_strategy(7500, 8192)["strategy"] in {"summarize_old", "rag", "rag_only"}

    big_msgs = [{"role": "system", "content": "Sistem"}] + [
        {"role": "user", "content": f"Mesaj {i} " + ("kelime " * 120)} for i in range(15)
    ]
    fitted, info = fit_messages_to_context(big_msgs, 2048)
    assert info["overflow"] is True
    assert len(fitted) < len(big_msgs)
    assert estimate_tokens(fitted) <= 2048


@pytest.mark.anyio
async def test_gw07_gw08_gw09_decoding_errors_fallback_cancellation():
    assert DECODING_PROFILES["factual"]["temperature"] <= 0.1
    assert DECODING_PROFILES["extract"]["temperature"] == 0.0
    assert DECODING_PROFILES["creative"]["temperature"] >= 0.7

    conn_err = classify_error(ConnectionRefusedError("connection refused"))
    assert isinstance(conn_err, ConnectionFailedError)
    assert "ollama serve" in str(conn_err).lower()
    assert isinstance(classify_error(RuntimeError("404 model not found")), ModelNotFoundError)

    cb = CircuitBreaker(failure_threshold=2, recovery_seconds=10.0)
    cb.record_failure("m1")
    assert not cb.is_open("m1")
    cb.record_failure("m1")
    assert cb.is_open("m1")

    fake = FakeProvider(responses=["Yedek model yanıtı"], fail_models={"broken:7b"})
    client = LLMClient({"fake": fake})
    res = await client.chat(
        [{"role": "user", "content": "Test"}],
        model="broken:7b",
        provider_name="fake",
        fallback_models=["good:7b"],
        max_retries=0,
    )
    assert res.model == "good:7b"
    assert "broken:7b" in res.fallback_note

    tok = CancellationToken()
    tok.cancel("test iptal")
    with pytest.raises(asyncio.CancelledError):
        await client.chat([{"role": "user", "content": "İptal"}], model="good:7b", provider_name="fake", cancel_token=tok)


@pytest.mark.anyio
async def test_gw11_gw12_gw13_gw14_gw15_structured_tools_cache_traces_budget():
    class _PlanOut(BaseModel):
        title: str
        steps: list[str]

    # GW-11: First output broken JSON, second output valid -> automatic repair!
    fake = FakeProvider(responses=["{broken json", json.dumps({"title": "Plan A", "steps": ["Adım 1", "Adım 2"]})])
    client = LLMClient({"fake": fake})
    parsed = await client.structured(
        [{"role": "user", "content": "Plan üret"}],
        _PlanOut,
        model="good:7b",
        provider_name="fake",
    )
    assert parsed.title == "Plan A"
    assert len(parsed.steps) == 2

    # GW-12: Tool calling fallback via ReAct JSON
    tool_fake = FakeProvider(
        responses=[
            json.dumps({"action": "add", "arguments": {"a": 4, "b": 6}, "final_answer": ""}),
        ]
    )
    tclient = LLMClient({"fake": tool_fake})
    out = await tclient.call_with_tools(
        [{"role": "user", "content": "4 + 6 kaç?"}],
        tools=[{"type": "function", "function": {"name": "add", "description": "toplar"}}],
        native_tools_supported=False,
        model="good:7b",
        provider_name="fake",
    )
    assert out["type"] == "tool_call"
    assert out["name"] == "add"
    assert out["arguments"] == {"a": 4, "b": 6}

    # GW-13: Cache skips private_user_data=True, caches when private_user_data=False
    c_fake = FakeProvider(responses=["Önbellek yanıtı"])
    cclient = LLMClient({"fake": c_fake})
    r_priv1 = await cclient.chat(
        [{"role": "user", "content": "Gizli veri sk-12345678901234567890123456"}],
        model="good:7b",
        provider_name="fake",
        use_cache=True,
        private_user_data=True,
    )
    r_priv2 = await cclient.chat(
        [{"role": "user", "content": "Gizli veri sk-12345678901234567890123456"}],
        model="good:7b",
        provider_name="fake",
        use_cache=True,
        private_user_data=True,
    )
    assert not r_priv1.cached and not r_priv2.cached

    # GW-14: Traces persisted and PII/secret redacted
    traces = get_run_traces(r_priv1.run_id)
    assert len(traces) == 1
    assert "sk-12345678901234567890123456" not in traces[0]["prompt_summary"]

    import uuid

    pub_q = f"Kamu sorusu {uuid.uuid4().hex}"
    r_pub1 = await cclient.chat(
        [{"role": "user", "content": pub_q}],
        model="good:7b",
        provider_name="fake",
        use_cache=True,
        private_user_data=False,
    )
    r_pub2 = await cclient.chat(
        [{"role": "user", "content": pub_q}],
        model="good:7b",
        provider_name="fake",
        use_cache=True,
        private_user_data=False,
    )
    assert not r_pub1.cached and r_pub2.cached

    # GW-15: Budget enforcement
    cclient.daily_token_budget = 1
    with pytest.raises(BudgetExceededError):
        await cclient.chat(
            [{"role": "user", "content": "Bütçe testi"}],
            model="good:7b",
            provider_name="fake",
            user_id="default",
        )


@pytest.mark.anyio
async def test_gw16_gw17_gw18_gw19_prompts_greeting_council_cascade():
    tpl = load_template("base_identity")
    assert tpl.version.startswith("1.")
    assert is_simple_greeting("merhaba")
    assert not is_simple_greeting("merhaba bana python ile dcf hesapla")

    p_greet, _ = build_layered_system_prompt(user_prompt="selam", memory_block="Kullanıcı Python seviyor")
    assert "Kullanıcı Python seviyor" not in p_greet

    p_real, _ = build_layered_system_prompt(user_prompt="Python ile kod yaz", memory_block="Kullanıcı Python seviyor")
    assert "Kullanıcı Python seviyor" in p_real

    fake = FakeProvider(responses=["Öneri A", "Öneri B", "Eleştiri", "Nihai sentez yanıtı."])
    client = LLMClient({"fake": fake})
    council = await client.run_council(
        "Mimari karar",
        proposer_models=["mA", "mB"],
        critic_model="mCrit",
        judge_model="mJudge",
        provider_name="fake",
    )
    assert "Nihai sentez" in council["final_answer"]
    assert len(fake.calls) == 4

    casc_fake = FakeProvider(responses=["Emin değilim.", "Güçlü modelin kesin yanıtı."])
    c2 = LLMClient({"fake": casc_fake})
    casc = await c2.cascade_chat(
        [{"role": "user", "content": "Zor soru"}],
        fast_model="small:4b",
        strong_model="big:14b",
        provider_name="fake",
    )
    assert casc["escalated"] is True
    assert casc["result"].model == "big:14b"


# ---------------------------------------------------------------- ORC-01..ORC-23 Tests

def test_orc01_pipeline_stage_functions_under_150_lines():
    """ORC-01: Every stage function in master/orchestrator/pipeline.py must be <= 150 lines."""
    src = (MASTER_DIR / "orchestrator" / "pipeline.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    oversized: list[tuple[str, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("stage_"):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > 150:
                oversized.append((node.name, length))
    assert oversized == [], f"Oversized stage functions (>150 lines): {oversized}"


def test_orc02_orc03_orc04_orc20_classifier_multi_intent_and_language():
    version, specs = load_intent_catalog()
    assert len(specs) == 30
    assert version

    dec = classify_intent("sadece kod ver: python fibonacci fonksiyonu")
    assert dec.intent == "code_only"
    assert dec.mode == "code_only"
    assert dec.latency_ms < 50.0

    subs = decompose_multi_intent("python kodu yaz sonra özetle ardından ingilizceye çevir")
    assert len(subs) == 3

    assert detect_language("Merhaba, bu konuyu açıklar mısın?") == "tr"
    assert detect_language("Please explain how Docker containers work") == "en"
    assert detect_language("Bunu İngilizce anlat") == "en"


@pytest.mark.anyio
async def test_orc05_orc06_plan_validation_and_parallel_dag():
    reg = build_default_registry()

    # Unknown tool rejected
    bad_tool = ExecutionPlan(
        plan_id="p1",
        goal="test",
        complexity="simple",
        mode="general",
        steps=[PlanStep(step_id="s1", action="tool", description="bad", tool="nonexistent_tool")],
    )
    with pytest.raises(PlanValidationError):
        validate_plan(bad_tool, reg)

    # Cycle rejected
    cyclic = ExecutionPlan(
        plan_id="p2",
        goal="test",
        complexity="multi_step",
        mode="general",
        steps=[
            PlanStep(step_id="a", action="llm", description="A", depends_on=["b"]),
            PlanStep(step_id="b", action="llm", description="B", depends_on=["a"]),
        ],
    )
    with pytest.raises(PlanValidationError):
        validate_plan(cyclic, reg)

    # Parallel independent steps run concurrently (2 x 0.15s should finish well under 0.28s)
    par_plan = ExecutionPlan(
        plan_id="p3",
        goal="parallel",
        complexity="multi_step",
        mode="general",
        steps=[
            PlanStep(step_id="left", action="llm", description="L"),
            PlanStep(step_id="right", action="llm", description="R"),
            PlanStep(step_id="join", action="llm", description="J", depends_on=["left", "right"]),
        ],
    )
    t0 = time.perf_counter()

    async def _runner(step: PlanStep, prior):
        await asyncio.sleep(0.12 if step.step_id in {"left", "right"} else 0.01)
        return f"ok:{step.step_id}"

    outcomes = await DAGExecutor().execute(par_plan, reg, _runner)
    elapsed = time.perf_counter() - t0
    assert outcomes["join"].status == "ok"
    assert elapsed < 0.24


@pytest.mark.anyio
async def test_orc08_orc09_orc10_tools_approval_gate_and_react_loop():
    reg = build_default_registry()

    # Read-only tool runs without approval
    r_calc = await reg.execute("calculator", {"expression": "(12 * 5) + 8"})
    assert r_calc.status == "ok"
    assert r_calc.output["result"] == 68

    # Write tool blocked without approval (ORC-09)
    r_blocked = await reg.execute("workspace_write_file", {"path": "a.py", "content": "x=1"}, approval_granted=False)
    assert r_blocked.status == "approval_required"

    # Succeeds once approved
    r_ok = await reg.execute("workspace_write_file", {"path": "a.py", "content": "x=1"}, approval_granted=True)
    assert r_ok.status == "ok"

    # ORC-10: Loop detector terminates repeated identical call
    async def _stuck_decider(_history):
        return {"tool": "calculator", "args": {"expression": "2+2"}}

    react = await run_react_loop(_stuck_decider, reg, max_steps=6)
    assert react.stopped_reason == "loop_detected"


def test_orc11_to_orc23_sse_jobs_artifacts_targeted_edit_clarification_memory_feedback():
    # ORC-11: All 13 SSE event types
    assert len(SSE_EVENT_TYPES) == 13
    ev = make_sse_event("route", {"intent": "lesson"}, run_id="run-1", seq=1)
    assert ev["schema_version"] == 1 and ev["type"] == "route"

    # ORC-12: Reconnectable jobs
    job = create_job("presentation", message="Hazırlanıyor")
    upd = update_job(job["job_id"], status="running", progress=60)
    assert upd and upd["progress"] == 60
    assert get_job(job["job_id"])["status"] == "running"

    # ORC-13 & ORC-16: Targeted edit leaves untouched sections byte-identical
    art = save_artifact(
        kind="presentation",
        title="Enerji Sunumu",
        sections=["Slayt 1: Giriş", "Slayt 2: Mevcut Durum", "Slayt 3: Eski Veri", "Slayt 4: Sonuç"],
    )
    edited = apply_targeted_edit(art["artifact_id"], 2, "Slayt 3: Güncel 2026 Verisi")
    assert edited["version"] == 2
    assert edited["sections"][0] == "Slayt 1: Giriş"
    assert edited["sections"][1] == "Slayt 2: Mevcut Durum"
    assert edited["sections"][2] == "Slayt 3: Güncel 2026 Verisi"
    assert edited["sections"][3] == "Slayt 4: Sonuç"
    assert get_artifact(art["artifact_id"])["version"] == 2

    # ORC-15: Clarification gate refuses guessing missing DCF inputs
    qs = check_clarification_needed("finance_dcf", "Şirket için DCF değerleme hesapla")
    assert 1 <= len(qs) <= 3

    # ORC-21: Memory relevance filter excludes unrelated memories
    mems = [
        {"fact": "Kullanıcı Python ve FastAPI ile backend geliştiriyor"},
        {"fact": "Kullanıcı İzmir'de yaşıyor"},
    ]
    rel_py = filter_relevant_memories("FastAPI backend endpointi nasıl yazılır", mems)
    assert len(rel_py) == 1 and "FastAPI" in rel_py[0]["fact"]
    rel_weather = filter_relevant_memories("Bugün hava durumu nasıl", mems)
    assert rel_weather == []

    # ORC-22: Feedback recording
    fb = record_feedback("run-demo", -1, reason_tags=["uzun", "kaynak yok"], note="Daha kısa olsun")
    assert fb["rating"] == -1
    summ = feedback_summary()
    assert summ["total"] >= 1


# ---------------------------------------------------------------- MODE-01..MODE-08 Tests

@pytest.mark.anyio
async def test_mode01_to_mode08_all_output_contracts():
    # MODE-02: code_only strips prose and checks Python AST
    c_code = build_contract("code_only")
    bad_code = "İşte istediğiniz kod:\n```python\ndef fib(n):\n    return n if n < 2 else fib(n-1)+fib(n-2)\n```\nUmarım işine yarar!"
    val_bad = validate_contract(bad_code, c_code)
    assert not val_bad.passed
    fixed_code, val_fixed = await enforce_contract(bad_code, c_code)
    assert val_fixed.passed
    assert "Umarım" not in fixed_code

    # MODE-02: broken Python syntax caught
    broken_py = "```python\ndef broken(:\n    pass\n```"
    assert not validate_contract(broken_py, c_code).passed

    # MODE-03: lesson 6-section checklist
    c_lesson = build_contract("lesson")
    good_lesson = (
        "### 1. Kısa Tanım\nÖzyineleme kendi kendini çağıran fonksiyondur.\n"
        "### 2. Sezgisel Benzetme\nİç içe geçmiş matruşka bebekleri gibidir.\n"
        "### 3. Adım Adım Açıklama\nTaban koşul ve küçülen alt problem tanımlanır.\n"
        "### 4. Çalışan Örnek\n```python\ndef f(n): return 1 if n <= 1 else n * f(n-1)\n```\n"
        "### 5. Sık Yapılan Hatalar\nTaban koşulu unutmak sonsuz döngüye yol açar.\n"
        "### 6. Mini Alıştırma\nFibonacci serisini özyineleme ile yaz."
    )
    assert validate_contract(good_lesson, c_lesson).passed
    assert not validate_contract("Sadece tek paragraf açıklama.", c_lesson).passed

    # MODE-04: research requires citations
    c_res = build_contract("research")
    assert not validate_contract("Katı hal pilleri enerji yoğunluğunu artırır.", c_res).passed
    assert validate_contract("Katı hal pilleri enerji yoğunluğunu artırır [1].", c_res).passed

    # MODE-05: presentation outline_first vs fast_generate
    c_pres_default = build_contract("presentation", user_text="Yapay zeka sunumu hazırla")
    assert c_pres_default.outline_first is True
    c_pres_fast = build_contract("presentation", user_text="Yapay zeka sunumu hemen oluştur")
    assert c_pres_fast.outline_first is False

    # MODE-06: project summary <= 120 words
    c_proj = build_contract("project")
    long_proj = "kelime " * 160
    fixed_proj, val_proj = await enforce_contract(long_proj, c_proj)
    assert val_proj.passed
    assert len(fixed_proj.split()) <= 120

    # MODE-07: short (<= 3 sentences, <= 45 words, zero preamble)
    c_short = build_contract("short")
    verbose = "Tabii ki! Docker uygulamaları izole konteynerlerde çalıştıran bir platformdur. Birinci cümle. İkinci cümle. Üçüncü cümle. Dördüncü cümle."
    fixed_short, val_short = await enforce_contract(verbose, c_short)
    assert val_short.passed
    assert not fixed_short.lower().startswith("tabii")

    # MODE-08: explicit format directives
    dirs = parse_format_directives("Bunu madde madde ve İngilizce anlat")
    assert "bullet_list" in dirs and "lang_en" in dirs
    c_dir = build_contract("general", user_text="Bunu madde madde anlat")
    repaired_bullets, val_bullets = await enforce_contract("Birinci nokta. İkinci nokta.", c_dir)
    assert val_bullets.passed
    assert repaired_bullets.startswith("- ")


# ---------------------------------------------------------------- ORC-24: 60 End-to-End Scenarios (30 Intents x 2)

SCENARIOS_60: list[tuple[str, str]] = [
    ("greeting", "merhaba"),
    ("greeting", "selam nasılsın"),
    ("chat", "bugün biraz sohbet edelim"),
    ("chat", "yeni fikirler üzerine konuşalım"),
    ("factual_qa", "türkiye cumhuriyeti ne zaman kuruldu"),
    ("factual_qa", "http ve https arasındaki fark nedir"),
    ("lesson", "bana özyineleme konusunu öğret"),
    ("lesson", "sql join kavramını sıfırdan anlat"),
    ("code_write", "python ile hızlı sıralama fonksiyonu yaz"),
    ("code_write", "fastapi ile crud endpointi oluştur"),
    ("code_only", "sadece kod ver: python fibonacci fonksiyonu"),
    ("code_only", "code only: binary search in python"),
    ("code_fix", "bu python kodundaki hatayı düzelt"),
    ("code_fix", "traceback keyerror neden oluyor debug et"),
    ("project_build", "tam bir e-ticaret web sitesi projesi oluştur"),
    ("project_build", "build a complete fullstack todo web application project"),
    ("game_build", "tarayıcıda oynanabilir yılan oyunu yap"),
    ("game_build", "html5 canvas ile tetris oyunu oluştur"),
    ("presentation", "yapay zeka tarihi hakkında powerpoint sunumu hazırla"),
    ("presentation", "10 slaytlık pptx sunum oluştur"),
    ("document_gen", "bu verilerle word raporu docx oluştur"),
    ("document_gen", "excel bütçe tablosu xlsx üret"),
    ("research", "kuantum bilgisayarların güncel durumunu kaynaklı araştır"),
    ("research", "deep research with citations on solid state batteries"),
    ("data_analysis", "bu csv veri setini analiz et ve ortalama bul"),
    ("data_analysis", "sql sorgusu yazıp aylık gelir dağılımını çıkar"),
    ("image_gen", "mimari akış diyagramı görseli çiz"),
    ("image_gen", "minimalist logo ve poster resmi oluştur"),
    ("image_explain", "bu fotoğrafta ne görüyorsun açıkla"),
    ("image_explain", "yüklediğim ekran görüntüsündeki hatayı incele"),
    ("audio_transcribe", "bu ses kaydını metne çevir"),
    ("audio_transcribe", "transcribe this audio recording to text"),
    ("translate", "bu metni ingilizceye çevir"),
    ("translate", "translate this technical specification to german"),
    ("summarize", "bu uzun makaleyi özetle"),
    ("summarize", "summarize the key takeaways of this document"),
    ("math_calc", "hesapla: (145 * 38) + 920 / 4"),
    ("math_calc", "bileşik faiz hesabı yap yüzde 12 ile"),
    ("legal_info", "kvkk kapsamında veri saklama yükümlülükleri nelerdir"),
    ("legal_info", "bu kira sözleşmesindeki riskli maddeleri incele"),
    ("finance_dcf", "şirket için dcf değerleme modeli hesapla"),
    ("finance_dcf", "indirgenmiş nakit akışı ve wacc hesabı yap"),
    ("health_info", "yüksek tansiyon belirtileri ve genel korunma yolları"),
    ("health_info", "d vitamini eksikliği nelere yol açar"),
    ("cnc_engineering", "cnc teknik resim balonlama ve gd&t tolerans analizi"),
    ("cnc_engineering", "iso 2768 tolerans tablosu ve freze kesme hızı"),
    ("file_convert", "gönderdiğim pdf dosyasını docx formatına çevir"),
    ("file_convert", "convert this pdf file into editable docx"),
    ("archive_zip", "bu klasörü zip dosyası olarak sıkıştır"),
    ("archive_zip", "extract this zip archive and inspect contents"),
    ("automation_mcp", "harici mcp connector ile bağlantı kur ve aracı çalıştır"),
    ("automation_mcp", "connect to external mcp server and run tool"),
    ("prompt_distill", "bu sohbeti yeniden kullanılabilir sistem promptu yap"),
    ("prompt_distill", "sohbeti prompt yap"),
    ("cross_chat", "diğer sohbetlerimde hangi projelerden bahsetmiştim"),
    ("cross_chat", "geçmiş sohbetler arası bilgi analizi yap"),
    ("short_answer", "kısaca tek cümlede açıkla: docker nedir"),
    ("short_answer", "briefly in one sentence what is kubernetes"),
    ("targeted_edit", "sadece 3. slaytı değiştir diğerlerine dokunma"),
    ("targeted_edit", "edit only section 2 and keep everything else untouched"),
]


def _canned_response_for_mode(mode: str, prompt: str = "") -> str:
    if mode == "code_only":
        return "```python\ndef solve(x):\n    return x * 2\n```"
    if mode == "lesson":
        return (
            "1. Kısa Tanım: Temel kavram.\n2. Sezgisel Benzetme: Günlük örnek.\n"
            "3. Adım Adım Açıklama: Aşamalar.\n4. Çalışan Örnek:\n```python\nprint(1)\n```\n"
            "5. Sık Yapılan Hatalar: Kenar durum.\n6. Mini Alıştırma: Kendin dene."
        )
    if mode == "research":
        return "Araştırma bulgusu güvenilir kaynakla doğrulandı [1]."
    if mode == "presentation":
        return "Slayt 1: Giriş\n\nSlayt 2: Gelişme\n\nSlayt 3: Sonuç"
    if mode == "project":
        return "Proje dosyaları çalışma alanında oluşturuldu ve önizlemeye hazır."
    if mode == "short":
        return "Kısa ve net yanıt verildi."
    if "tablo" in prompt.lower() or "table" in prompt.lower():
        return "| Kalem | Değer |\n| --- | --- |\n| Bütçe | 1000 |"
    return "İstek başarıyla işlendi."


@pytest.mark.anyio
async def test_orc24_sixty_scenarios_end_to_end():
    """ORC-24: Run all 60 scenarios (30 intents x 2) through the full 8-stage pipeline."""
    import uuid

    assert len(SCENARIOS_60) == 60
    run_tag = uuid.uuid4().hex[:6]
    correct_intents = 0
    for idx, (expected_intent, prompt) in enumerate(SCENARIOS_60):
        dec = classify_intent(prompt)
        if dec.intent == expected_intent:
            correct_intents += 1
        fake = FakeProvider(responses=[_canned_response_for_mode(dec.mode, prompt)])
        client = LLMClient({"fake": fake})
        cid = f"chat-sc-{run_tag}-{idx}"
        ctx = await run_pipeline(
            prompt,
            user_id="scenario-user",
            chat_id=cid,
            client=client,
            seed=42,
        )
        assert ctx.final_response
        assert any(e["type"] == "done" for e in ctx.events)
        assert get_run(ctx.run_id) is not None
        if not ctx.clarification_questions and ctx.validation is not None:
            assert ctx.validation.passed, f"Scenario {idx} ({expected_intent}) failed contract: {ctx.validation.violations}"
        if idx == 0:
            st = load_conversation_state(cid, "scenario-user")
            assert st.turn_count == 1

    accuracy = correct_intents / len(SCENARIOS_60)
    assert accuracy >= 0.95, f"Intent accuracy below 95%: {correct_intents}/60 ({accuracy:.1%})"


def test_gateway_and_orchestrator_http_endpoints():
    """GW-20 & ORC-23: Verify mounted FastAPI endpoints on master/app.py."""
    with TestClient(master_app.app) as client:
        r_status = client.get("/api/gateway/status")
        assert r_status.status_code == 200
        assert "providers" in r_status.json()

        r_intents = client.get("/api/orchestrator/intents")
        assert r_intents.status_code == 200
        assert r_intents.json()["count"] == 30

        r_tools = client.get("/api/orchestrator/tools")
        assert r_tools.status_code == 200
        assert len(r_tools.json()["tools"]) >= 5
