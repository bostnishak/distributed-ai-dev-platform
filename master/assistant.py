"""Assistant tab: the chat assistant (PB-36/37).

Sprint 3: LiteLLM gateway removed. The assistant now calls Ollama directly on the master.
Vision requests (image uploads) are routed to an online agent that has vision capability; if
none is available the master's own model is used instead (qwen3.5:4b supports vision).
"""

import ast
import asyncio
import json
import logging
import operator
import os
import re
import sqlite3
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

import code_verify
import config
import data_lab
import db
import reasoning_mode
import untrusted
from access_control import require_local_or_admin
from assistant_cad_cnc import (  # noqa: F401
    CNC_BALLOON_KEYWORDS,
    CODE_ONLY_RE,
    PROJECT_ACTION_RE,
    PROJECT_NOUN_RE,
)
from assistant_cad_cnc import detect_project_type as _detect_project_type  # noqa: F401
from assistant_cad_cnc import is_3d_cad_request as _is_3d_cad_request  # noqa: F401
from assistant_cad_cnc import is_cnc_balloon_request as _is_cnc_balloon_request  # noqa: F401
from assistant_cad_cnc import is_project_build_request as _is_project_build_request  # noqa: F401
from assistant_cad_cnc import is_zip_workspace_request as _is_zip_workspace_request  # noqa: F401
from assistant_cad_cnc import run_3d_cad_cam_from_chat as _run_3d_cad_cam_from_chat  # noqa: F401
from assistant_cad_cnc import run_cnc_balloon_from_chat as _run_cnc_balloon_from_chat  # noqa: F401
from assistant_cad_cnc import try_extended_calculation as _try_extended_calculation
from assistant_prep import (
    build_domain_enrichment_notes,
    build_llm_stream_inputs,
    build_media_file_response,
    create_llm_stream_response,
    enrich_done_event_with_verification,
    enrich_prompt_with_kb,
    parse_stream_opts,
    process_uploaded_attachment,
)
from assistant_stream_fastpaths import (
    _history_has_messages,
    dispatch_chat_fastpath,
    single_token_stream,
)
from chat_queue import with_queue_notice
from prompt_loader import load_prompt

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assistant", tags=["assistant"])
DEFAULT_TASK = "genel"

_EMOJI_STRIP_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U00002712"
    "\U00002728\U0000274C\U00002753-\U00002755\U00002764\u200d\ufe0f]+",
    flags=re.UNICODE,
)
_FENCED_CODE_SPLIT_RE = re.compile(r"(```[\s\S]*?```)")


def _strip_emojis(text: str) -> str:
    """DEF-23: Strip emojis outside fenced code blocks while preserving technical symbols (→, ✓, ≤, ©)."""
    if not text:
        return text
    parts = _FENCED_CODE_SPLIT_RE.split(text)
    for idx in range(0, len(parts), 2):
        parts[idx] = _EMOJI_STRIP_RE.sub("", parts[idx])
    return "".join(parts)


ANSWER_SYSTEM_PROMPT = load_prompt("b1_answer_system.txt")

_INSULT_RE = re.compile(r"\b(?:orospu\w*|piç\w*|siktir\w*|amk|aq|yarrak\w*|göt\s*veren\w*|fuck\s+you|motherfucker\w*|bitch\w*)\b", re.IGNORECASE)
_OLLAMA_TAGS_CACHE: dict[str, Any] = {"ts": 0.0, "models": set()}


async def _select_grounded_model(task_type: str, has_image: bool = False) -> str:
    """Pick the strongest installed local Ollama model for the task to minimize hallucinations."""
    now = time.monotonic()
    if now - _OLLAMA_TAGS_CACHE["ts"] > 30.0 or not _OLLAMA_TAGS_CACHE["models"]:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                r = await client.get(f"{config.OLLAMA_URL}/api/tags")
                if r.status_code == 200:
                    _OLLAMA_TAGS_CACHE["models"] = {m.get("name", "") for m in r.json().get("models", [])}
                    _OLLAMA_TAGS_CACHE["ts"] = now
        except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            log.debug("Recoverable error suppressed: %s", exc)
    installed = _OLLAMA_TAGS_CACHE["models"]
    if has_image:
        prefs = ("qwen3.5:9b", "gemma4:e4b", "qwen3.5:4b", config.MASTER_MODEL)
    elif task_type == "kod":
        prefs = ("qwen3.5:9b", "qwen2.5-coder:7b", "qwen3.5:4b", config.MASTER_MODEL)  # the larger model invents fewer APIs
    else:
        prefs = ("qwen3.5:9b", "qwen2.5-coder:7b", "qwen3.5:4b", config.MASTER_MODEL)
    for cand in prefs:
        if cand in installed:
            return cand
    return config.MASTER_MODEL


CODE_KEYWORDS = (
    "python", "javascript", "typescript", "java ", "c++", "c#", " sql",
    "kod yaz", "kodu yaz", "fonksiyon yaz", "script yaz", "program yaz",
    "uygulama yap", "uygulama yaz", "algoritma yaz", "class yaz", "sinif yaz",
    "hata ayikla", "debug et", "kodda hata", "bug'i duzelt", "hesap makinesi",
)


def _find_vision_agent() -> dict[str, Any] | None:
    """Return an online agent that has vision capability, or None (PB-36)."""
    for agent in db.list_agents():
        if "vision" not in (agent.get("capabilities") or []):
            continue
        last_seen = agent.get("last_seen_at")
        if not last_seen:
            continue
        ts = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if (datetime.now(UTC) - ts).total_seconds() < 30:
            return agent
    return None


async def call_ollama_chat(
    prompt: str,
    system_prompt: str | None = None,
    image_b64: str | None = None,
    task_type: str = "genel",
) -> tuple[str, str]:
    """Call master's local Ollama with grounded strongest-model selection. Returns (content, model_used)."""
    ollama_url = config.OLLAMA_URL
    if task_type == "classifier":
        model = config.MASTER_MODEL
    else:
        try:
            model = await _select_grounded_model(task_type, has_image=bool(image_b64))
        except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, AttributeError):
            model = config.MASTER_MODEL
    if image_b64:
        _find_vision_agent()

    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    user_msg: dict[str, Any] = {"role": "user", "content": prompt}
    if image_b64:
        user_msg["images"] = [image_b64]
    messages.append(user_msg)

    import gateway

    gw = (
        gateway.default_client
        if ollama_url.rstrip("/") == config.OLLAMA_URL.rstrip("/")
        else gateway.LLMClient({"ollama": gateway.OllamaProvider(base_url=ollama_url)})
    )
    try:
        res = await gw.chat(
            messages, model=model, profile="creative", num_predict=config.ASSISTANT_NUM_PREDICT,
            timeout_s=180.0, feature="assistant_chat", max_retries=0,
        )
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Ollama hatası: {exc}") from exc
    return res.content, model


def keyword_category_override(prompt: str) -> str | None:
    lowered = prompt.lower()
    return "kod" if any(kw in lowered for kw in CODE_KEYWORDS) else None


def _safe_pow(base: float, exp: float) -> float:
    if abs(exp) > 1000 or abs(base) > 10**6:
        raise ValueError("expression too large")
    return operator.pow(base, exp)


_SAFE_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: _safe_pow,
}
_SAFE_UNARY_OPS: dict[type[ast.unaryop], Any] = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_ARITHMETIC_ONLY = re.compile(r"^[\d\s()+\-*/.%^]+$")
_HAS_OPERATOR = re.compile(r"\d\s*[+\-*/%^]\s*[\d(]")
_CALC_TRAILING_WORDS = re.compile(r"(kaç\s*eder|kaç\s*yapar|nedir|hesapla|sonucu\s*ne|eşittir)\s*\??\s*$", re.IGNORECASE)


def _safe_eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BIN_OPS:
        return float(_SAFE_BIN_OPS[type(node.op)](_safe_eval_node(node.left), _safe_eval_node(node.right)))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARY_OPS:
        return float(_SAFE_UNARY_OPS[type(node.op)](_safe_eval_node(node.operand)))
    raise ValueError("unsupported expression")


def try_calculate(prompt: str) -> str | None:
    """Return 'expression = result' for deterministic math/unit/finance expressions; otherwise None."""
    import chat_contracts

    if (extended := _try_extended_calculation(prompt)) is not None:
        return extended
    text = _CALC_TRAILING_WORDS.sub("", prompt.strip()).strip().rstrip("?").strip()
    if not text or len(text) > 200 or not _ARITHMETIC_ONLY.match(text) or not _HAS_OPERATOR.search(text):
        return chat_contracts.extract_deterministic_calculation(prompt)
    try:
        result: float | int = _safe_eval_node(ast.parse(text.replace("^", "**"), mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError, OverflowError, RecursionError):
        return chat_contracts.extract_deterministic_calculation(prompt)
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{text} = {result}"


async def classify_and_moderate(prompt: str) -> tuple[str, bool]:
    """One classifier call decides both the task category and whether the message is insulting."""
    if not config.CLASSIFIER_USE_LLM:  # a model call per message cost 5-13 s; keywords decide, the LLM stays optional
        return DEFAULT_TASK, bool(_INSULT_RE.search(prompt))
    classifier_prompt = load_prompt("b1_classifier_prompt.txt").replace("{prompt}", prompt)
    try:
        result, _ = await call_ollama_chat(classifier_prompt, task_type="classifier")
    except HTTPException:
        return DEFAULT_TASK, False
    return parse_classifier_response(result)


def parse_classifier_response(result: str) -> tuple[str, bool]:
    """Parse the classifier's raw answer; a pure function so it is testable without a model."""
    cleaned = result.replace("*", "").replace("<", "").replace(">", "")
    category_match = re.search(r"KATEGORI:\s*(kod|genel)\b", cleaned, re.IGNORECASE)
    category = category_match.group(1).lower() if category_match else DEFAULT_TASK
    inappropriate_match = re.search(r"UYGUNSUZ:\s*(evet|hayir)\b", cleaned, re.IGNORECASE)
    inappropriate = bool(inappropriate_match and inappropriate_match.group(1).lower() == "evet")
    return category, inappropriate


class ChatResponse(BaseModel):
    content: str
    used_model: str
    task_type: str


async def _prepare_chat_request(
    prompt: str, file: UploadFile | None
) -> tuple[str, str | None, str | None, str, bool]:
    """Shared pre-processing for both /chat and /chat/stream."""
    extracted_text, image_b64, forced_task_type, file_note = "", None, None, ""
    if file is not None and file.filename:
        extracted_text, image_b64, forced_task_type, file_note = await process_uploaded_attachment(file, prompt)
        extracted_text = untrusted.guard(extracted_text)
    file_note += build_domain_enrichment_notes(prompt, extracted_text)
    full_prompt = enrich_prompt_with_kb(prompt, extracted_text) + file_note
    if file is not None and file.filename:
        full_prompt += await data_lab.verified_facts(prompt, file.filename, extracted_text)
    keyword_task = forced_task_type or keyword_category_override(prompt)
    inappropriate = False
    if not keyword_task:
        _, inappropriate = await classify_and_moderate(prompt)
    return full_prompt, image_b64, forced_task_type, keyword_task or "", inappropriate


@router.post("/chat", response_model=ChatResponse)
async def chat(prompt: str = Form(...), file: UploadFile | None = File(None)):  # noqa: B008
    if file is None or not file.filename:
        if (calc_result := try_calculate(prompt)) is not None:
            return ChatResponse(content=calc_result, used_model="hesaplama", task_type="hesaplama")
    full_prompt, image_b64, _forced, keyword_task, inappropriate = await _prepare_chat_request(prompt, file)
    if inappropriate:
        return ChatResponse(
            content=(
                "Bu mesaj hakaret/uygunsuz ifade içerebilecek şekilde değerlendirildi, "
                "bu yüzden bir modele iletilmedi. Lütfen sorunu farklı bir şekilde ifade et."
            ),
            used_model="moderation",
            task_type="engellendi",
        )
    resolved_task = keyword_task or DEFAULT_TASK
    content, used_model = await call_ollama_chat(
        full_prompt, system_prompt=ANSWER_SYSTEM_PROMPT, image_b64=image_b64, task_type=resolved_task
    )
    return ChatResponse(content=content, used_model=used_model, task_type=resolved_task)


@router.get("/media/{filename}")
async def get_assistant_media(filename: str):
    """Serve generated or edited images (.png, .svg) and documents (.xlsx, .docx, .pdf)."""
    return build_media_file_response(filename)


def _persist_stream_usage(
    meta: tuple[str, str, str, str],
    prompt: str,
    answer: str,
    metrics: tuple[int, int, int, bool],
) -> None:
    import memory_engine as mem
    import user_profile as up

    user_id, conversation_id, model_used, task_type = meta
    p_tok, c_tok, latency_ms, estimated = metrics
    try:
        up.record_usage(user_id, conversation_id, model_used, task_type, p_tok, c_tok, latency_ms, estimated)
        if conversation_id and answer.strip():
            learn = bool(up.get_settings(user_id).get("auto_learn_facts"))
            mem.record_conversation_turn(conversation_id, prompt, answer, model_used, task_type, user_id=user_id, learn=learn)
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        log.warning("Failed to record usage/memory turn: %s", exc, exc_info=True)


async def _tracked_stream(source, prompt: str, user_id: str, conversation_id: str):
    """Wrap an SSE generator: measure latency, enrich verification, and persist usage & memory."""
    import user_profile as up

    started = time.monotonic()
    collected: list[str] = []
    async for chunk in source:
        text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, (bytes, bytearray)) else chunk
        if not text.startswith("data: "):
            yield chunk
            continue
        try:
            evt = json.loads(text[6:].strip())
        except json.JSONDecodeError:
            yield chunk
            continue
        if evt.get("type") == "token":
            collected.append(evt.get("content", ""))
            yield chunk
        elif evt.get("type") == "done":
            model_used, task_type = evt.get("model", ""), evt.get("task_type", "")
            answer = "".join(collected)
            usage = evt.get("usage") or {}
            p_tok = int(usage.get("prompt_tokens") or up.estimate_tokens(prompt))
            c_tok = int(usage.get("completion_tokens") or up.estimate_tokens(answer))
            latency_ms = round((time.monotonic() - started) * 1000)
            evt["usage"] = {"prompt_tokens": p_tok, "completion_tokens": c_tok, "estimated": not usage}
            evt["latency_ms"] = latency_ms
            await enrich_done_event_with_verification(evt, prompt, answer, (model_used, conversation_id))
            _persist_stream_usage((user_id, conversation_id, model_used, task_type), prompt, answer, (p_tok, c_tok, latency_ms, not usage))
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        else:
            yield chunk


@router.post("/chat/stream")
async def chat_stream(
    prompt: str = Form(...),
    file: UploadFile | None = File(None),  # noqa: B008
    history: str = Form("[]"),
    opts: dict[str, str] = Depends(parse_stream_opts),  # noqa: B008
):
    """Streaming chat endpoint with optional modelPicker override and custom agent binding (SOH-07, AJN-01)."""
    import user_profile as up

    try:
        uid = up.valid_user_id(opts["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if len(history) > config.MAX_HISTORY_FIELD_BYTES:
        raise HTTPException(413, "Sohbet geçmişi çok uzun; yeni bir sohbet başlat.")
    reasoning_mode.mark(prompt)
    stream_meta = {**opts, "user_id": uid}
    resp = await _chat_stream_impl(prompt, file, history, stream_meta)
    resp.body_iterator = with_queue_notice(code_verify.wrap(_tracked_stream(resp.body_iterator, prompt, uid, stream_meta["conversation_id"]), prompt))
    return resp


def _is_prompt_conversion_request(prompt: str) -> bool:
    """Detect when the user wants to convert the current (or another) chat into a reusable master prompt."""
    low = (prompt or "").lower()
    if not any(k in low for k in ("prompt", "istem")):
        return False
    conv_verbs = (
        "haline çevir", "haline cevir", "haline getir", "prompt yap", "prompta çevir", "prompta cevir",
        "prompta dönüştür", "prompta donustur", "prompt olarak", "prompt oluştur", "prompt olustur",
        "master prompt", "tek prompt", "başka yerde kullan", "baska yerde kullan",
        "turn this chat", "convert this chat", "convert conversation",
    )
    chat_refs = (
        "sohbet", "chat", "geçmiş", "gecmis", "konuşma", "konusma", "baştan sona", "bastan sona",
        "başka yerde", "baska yerde", "master prompt", "tek prompt", "prompt haline", "prompta çevir",
        "prompta cevir", "prompta dönüştür", "prompta donustur", "this chat", "conversation",
    )
    return any(v in low for v in conv_verbs) and any(r in low for r in chat_refs)


PROMPT_CONVERSION_SYSTEM_INSTRUCTION = (
    "--- SOHBETI MASTER PROMPTA DONUSTURME GOREVI ---\n"
    "Kullanici bu sohbet gecmisinin tamamini (veya belirttigi baska bir sohbeti) baska yapay zeka "
    "araclarinda bastan sona kullanabilecegi tek, eksiksiz ve kopyalanabilir bir Master Prompt haline "
    "cevirmeni istiyor.\n"
    "KURALLAR:\n"
    "1. Sohbetteki tum amaclari, kullanici tercihlerini, teknik/icerik kararlarini, kisitlamalari, "
    "ornekleri ve simdiye kadar uretilen ciktilari eksiksiz ozetle; hicbir onemli detayi atlama.\n"
    "2. Ciktiyi dogrudan kopyalanip baska bir modele yapistirilabilecek tek bir ```text ... ``` kod "
    "blogu icinde ver.\n"
    "3. Master Prompt su bolumleri icersin: [ROL VE UZMANLIK], [BAGLAM VE AMAC], "
    "[GEREKSINIMLER VE KISITLAMALAR], [SIMDIYE KADAR YAPILANLAR / KARARLAR], [BEKLENEN CIKTI VE SONRAKI ADIM].\n"
    "4. Kod blogunun altina en fazla 2 cumlelik kisa bir kullanim notu ekle. Emoji kullanma."
)


async def _chat_stream_impl(
    prompt: str, file: UploadFile | None, history: str, meta: dict[str, str]
):
    from assistant_prep import resolve_custom_agent_profile

    user_id, conversation_id = meta["user_id"], meta["conversation_id"]
    has_file = bool(file is not None and file.filename)
    is_prompt_conv = (not has_file) and _is_prompt_conversion_request(prompt)
    if (fast := await dispatch_chat_fastpath(prompt, file, history, is_prompt_conv)) is not None:
        return fast
    if not has_file and (calc_result := try_calculate(prompt)) is not None:
        return single_token_stream(calc_result, "hesaplama", "hesaplama")
    full_prompt, image_b64, _forced, keyword_task, inappropriate = await _prepare_chat_request(prompt, file)
    if inappropriate:
        msg = (
            "Bu mesaj hakaret/uygunsuz ifade içerebilecek şekilde değerlendirildi, "
            "bu yüzden bir modele iletilmedi. Lütfen sorunu farklı bir şekilde ifade et."
        )
        return single_token_stream(msg, "moderation", "engellendi")
    task_type = keyword_task or DEFAULT_TASK
    agent_prof = resolve_custom_agent_profile(meta.get("custom_agent_id", ""), user_id)
    picked_model = meta.get("model", "") or (agent_prof.get("model", "") if agent_prof else "")
    model = picked_model or await _select_grounded_model(task_type, has_image=bool(image_b64))
    ctx = {
        "prompt": prompt, "full_prompt": full_prompt, "image_b64": image_b64,
        "history": history, "user_id": user_id, "conversation_id": conversation_id,
        "has_file": has_file, "is_prompt_conv": is_prompt_conv, "custom_agent": agent_prof,
    }
    messages, pre_note, constraints, research_sources = await asyncio.to_thread(
        build_llm_stream_inputs, ctx, ANSWER_SYSTEM_PROMPT, PROMPT_CONVERSION_SYSTEM_INSTRUCTION
    )
    return create_llm_stream_response(
        {
            "messages": messages, "pre_note": pre_note, "constraints": constraints,
            "research_sources": research_sources, "model": model, "task_type": task_type,
            "user_id": user_id, "prompt": prompt, "has_file": has_file, "is_prompt_conv": is_prompt_conv,
        },
        _strip_emojis,
    )


class CodeRunRequest(BaseModel):
    code: str


class CodeRunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


CODE_RUN_TIMEOUT_SECONDS = 5
CODE_RUN_MEMORY_LIMIT_MB = 128
NOBODY_ID = 65534


def _limit_code_run_resources() -> None:
    """Passed to subprocess.run as preexec_fn (POSIX only) to cap CPU time and memory."""
    import resource

    setrlimit = getattr(resource, "setrlimit", None)
    rlimit_cpu = getattr(resource, "RLIMIT_CPU", None)
    rlimit_as = getattr(resource, "RLIMIT_AS", None)
    if setrlimit is not None and rlimit_cpu is not None and rlimit_as is not None:
        setrlimit(rlimit_cpu, (CODE_RUN_TIMEOUT_SECONDS, CODE_RUN_TIMEOUT_SECONDS))
        mem_bytes = CODE_RUN_MEMORY_LIMIT_MB * 1024 * 1024
        setrlimit(rlimit_as, (mem_bytes, mem_bytes))


def _code_run_env() -> dict[str, str]:
    """A minimal environment: the run must not see the master's secrets through os.environ."""
    env = {"PYTHONIOENCODING": "utf-8"}
    if sys.platform == "win32":
        for key in ("SYSTEMROOT", "PATH"):
            if key in os.environ:
                env[key] = os.environ[key]
    return env


def _run_code_blocking(code: str) -> CodeRunResponse:
    """SEC-13: Run code strictly inside the hardened Docker container sandbox (never on host)."""
    import sandbox

    res = sandbox.run_python_code(code, timeout_s=CODE_RUN_TIMEOUT_SECONDS)
    if not res.get("docker_available"):
        raise HTTPException(
            status_code=503,
            detail=res.get("stderr") or "Docker sandbox erişilemiyor; ana makinede kod çalıştırma kapalı.",
        )
    return CodeRunResponse(
        stdout=str(res.get("stdout") or "")[-4000:],
        stderr=str(res.get("stderr") or "")[-4000:],
        exit_code=int(res.get("exit_code", -1)),
        timed_out=bool(res.get("timed_out", False)),
    )


def _optional_pkg_capability(pkg_name: str, install_hint: str) -> dict[str, object]:
    import importlib.util

    ok = importlib.util.find_spec(pkg_name) is not None
    return {"available": ok, "reason": "Hazır" if ok else f"Kurulu değil ({install_hint})"}


@router.get("/config")
async def assistant_config():
    """DEF-15: Tells the web UI which optional Assistant features and capabilities are available."""
    import sandbox

    sb = sandbox.status()
    searx_ok = bool(os.environ.get("SEARXNG_URL", "").strip())
    return {
        "code_run_enabled": bool(config.CODE_RUN_ENABLED and sb["available"]),
        "sandbox_available": sb["available"],
        "sandbox_reason": sb["reason"],
        "capabilities": {
            "stt": _optional_pkg_capability("faster_whisper", "pip install faster-whisper"),
            "tts": {"available": True, "reason": "Tarayıcı Web Speech API"},
            "ocr": _optional_pkg_capability("pytesseract", "pip install pytesseract"),
            "web_search": {"available": searx_ok, "reason": "SearXNG yapılandırıldı" if searx_ok else "SEARXNG_URL tanımlı değil"},
            "image_gen": _optional_pkg_capability("PIL", "pip install pillow"),
            "sandbox": {"available": sb["available"], "reason": sb["reason"]},
            "vector_index": _optional_pkg_capability("numpy", "pip install numpy"),
        },
    }


@router.post("/run-code", response_model=CodeRunResponse, dependencies=[Depends(require_local_or_admin)])
async def run_code(body: CodeRunRequest):
    """SEC-13: Execute Python snippet strictly inside the hardened Docker sandbox container."""
    from audit_log import AuditTrail

    if not config.CODE_RUN_ENABLED:
        raise HTTPException(status_code=403, detail="Kod çalıştırma bu sunucuda kapalı (CODE_RUN_ENABLED).")
    AuditTrail().append_event(actor="admin", action="SANDBOX_RUN_CODE", payload={"code_len": len(body.code or "")})
    return await asyncio.to_thread(_run_code_blocking, body.code)


@router.post("/transcribe")
async def transcribe_voice_clip(file: UploadFile = File(...)):  # noqa: B008
    """Transcribe a live microphone WAV/WebM recording locally to Turkish text."""
    import multimodal_studio as mms

    raw = await file.read()
    if not raw or len(raw) < 128:
        raise HTTPException(status_code=400, detail="Ses kaydı boş veya çok kısa.")
    return await asyncio.to_thread(mms.transcribe_audio_bytes, file.filename or "mic.wav", raw)


@router.get("/enterprise-status")
async def enterprise_status():
    """Return live telemetry, Thompson Bandit Router state, LLMOps DPO status, and ELO Arena leaderboard."""
    import cluster_telemetry as ct
    import enterprise_security_mcp as esm
    import llmops_pipeline as lp
    import media_lab_arena as mla

    return {
        "telemetry": ct.get_local_hardware_telemetry(query_ollama=False),
        "llmops": lp.get_llmops_stats(),
        "audit_chain_valid": esm.AuditTrail().verify_chain(),
        "elo_leaderboard": mla.CognitiveArena().get_leaderboard()[:5],
    }


__all__ = [
    "ANSWER_SYSTEM_PROMPT", "CODE_KEYWORDS", "DEFAULT_TASK", "PROMPT_CONVERSION_SYSTEM_INSTRUCTION",
    "ChatResponse", "CodeRunRequest", "CodeRunResponse", "_history_has_messages",
    "_is_prompt_conversion_request", "_strip_emojis", "call_ollama_chat", "classify_and_moderate",
    "keyword_category_override", "parse_classifier_response", "router", "try_calculate"]
