"""Requirements analysis and basic task decomposition (Sprint 1 scope).

The master model turns a requirements document into a structured ``RequirementsSpec``.
A deterministic template then turns the spec into a dependency graph (DAG) of tasks.
In Sprint 1 tasks are only planned; capability-based distribution to agents (Sprint 2)
and execution (Sprint 3) come later.
"""

import math
import re
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ValidationError

import config

# --- Specification schema (also sent to Ollama as the structured-output format) -----------


class EntityField(BaseModel):
    name: str
    type: str
    required: bool


class Entity(BaseModel):
    name: str
    description: str
    fields: list[EntityField]


class Endpoint(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    description: str
    entity: str


class Page(BaseModel):
    name: str
    description: str
    entities: list[str]


class RequirementsSpec(BaseModel):
    project_name: str
    summary: str
    actors: list[str]
    entities: list[Entity]
    api_endpoints: list[Endpoint]
    pages: list[Page]
    non_functional: list[str]
    open_questions: list[str]


SYSTEM_PROMPT = """You are the master agent of a distributed AI software development platform.
Read the software requirements document and extract a structured specification of the web
application it describes. The application will be built with an HTML/CSS/JavaScript frontend,
a Python FastAPI backend and a SQLite database.

Rules:
- Use only what the document states or clearly implies. Never invent features, fields or pages.
- If something needed to build the application is ambiguous or missing (for example user roles,
  validation rules, limits or business rules), add a short question to "open_questions" instead
  of guessing.
- Write every name, description and question in the same language as the document.
- Keep descriptions short (at most 15 words).
- entities: the data the application stores, with their fields. Field types: string, text,
  integer, number, boolean, date, datetime.
- api_endpoints: REST endpoints such as "GET /api/books" or "PUT /api/books/{id}". "entity" is
  the name of the entity the endpoint works on, or an empty string.
- pages: the screens of the web interface. "entities" lists the entity names each page shows.
- actors: only the names of the user roles or external systems (one to three words each,
  no descriptions).
- non_functional: performance, security, usability and similar requirements.
"""

CHUNK_NOTE = """
This is part {index} of {total} of a longer document. Extract only what this part contains;
the parts are merged afterwards.
"""

# Rough size estimate. Turkish and English text average roughly 3-4 characters per token, so
# dividing by 3 errs on the side of a larger context window.
CHARS_PER_TOKEN = 3
MIN_NUM_CTX = 8192
# Room for the wrapper text around the document in the user message.
MESSAGE_OVERHEAD_TOKENS = 200

MAX_ENTITIES = 40
MAX_ENDPOINTS = 120
MAX_PAGES = 40
MAX_LIST_ITEMS = 40

BACKEND_ENTITIES_PER_TASK = 2
FRONTEND_PAGES_PER_TASK = 2

ChatFn = Callable[[str, str, dict, int], Awaitable[str]]


class AnalysisError(RuntimeError):
    pass


@dataclass
class AnalysisResult:
    spec: RequirementsSpec
    chunk_count: int


# --- Sizing and chunking ------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def context_window_for(prompt_tokens: int) -> int:
    """Smallest power-of-two context (>= MIN_NUM_CTX) that fits prompt + answer, capped."""
    needed = prompt_tokens + config.NUM_PREDICT
    num_ctx = MIN_NUM_CTX
    while num_ctx < needed:
        num_ctx *= 2
    return min(num_ctx, config.NUM_CTX_MAX)


def max_chunk_chars() -> int:
    """Largest document part that still fits the capped context window in one request."""
    system_tokens = estimate_tokens(SYSTEM_PROMPT + CHUNK_NOTE)
    free_tokens = config.NUM_CTX_MAX - config.NUM_PREDICT - system_tokens - MESSAGE_OVERHEAD_TOKENS
    return max(free_tokens, 1000) * CHARS_PER_TOKEN


def normalize_document(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _split_oversized(block: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for line in block.split("\n"):
        while len(line) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:max_chars])
            line = line[max_chars:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_chars:
            current = candidate
        else:
            pieces.append(current)
            current = line
    if current:
        pieces.append(current)
    return pieces


def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split at paragraph (blank line) boundaries so headings stay with their sections."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        pieces = _split_oversized(block, max_chars) if len(block) > max_chars else [block]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return chunks


# --- Merging and cleaning -----------------------------------------------------------------

_TR_ASCII = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})


def slug(value: str) -> str:
    """Comparison key that ignores case, spacing, punctuation and Turkish diacritics."""
    ascii_key = re.sub(r"[^a-z0-9]", "", value.translate(_TR_ASCII).lower())
    return ascii_key or " ".join(value.split()).casefold()


def _dedupe(values: Iterable[str], limit: int = MAX_LIST_ITEMS) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = " ".join(value.split())
        if value and slug(value) not in seen:
            seen.add(slug(value))
            result.append(value)
    return result[:limit]


def merge_specs(specs: list[RequirementsSpec]) -> RequirementsSpec:
    """Combine partial specs (one per chunk) and clean a single spec the same way."""
    entities: dict[str, Entity] = {}
    for spec in specs:
        for entity in spec.entities:
            name = " ".join(entity.name.split())
            if not name:
                continue
            target = entities.setdefault(
                slug(name), Entity(name=name, description=entity.description.strip(), fields=[])
            )
            if not target.description:
                target.description = entity.description.strip()
            known = {slug(f.name) for f in target.fields}
            for field in entity.fields:
                field_name = field.name.strip()
                if field_name and slug(field_name) not in known:
                    known.add(slug(field_name))
                    target.fields.append(EntityField(
                        name=field_name, type=field.type.strip() or "string", required=field.required
                    ))

    endpoints: dict[tuple[str, str], Endpoint] = {}
    for spec in specs:
        for endpoint in spec.api_endpoints:
            path = endpoint.path.strip()
            if not path:
                continue
            if not path.startswith("/"):
                path = "/" + path
            endpoints.setdefault(
                (endpoint.method, path.rstrip("/").lower() or "/"),
                Endpoint(
                    method=endpoint.method, path=path,
                    description=endpoint.description.strip(), entity=endpoint.entity.strip(),
                ),
            )

    pages: dict[str, Page] = {}
    for spec in specs:
        for page in spec.pages:
            name = " ".join(page.name.split())
            if not name:
                continue
            target = pages.setdefault(slug(name), Page(name=name, description=page.description.strip(), entities=[]))
            if not target.description:
                target.description = page.description.strip()
            target.entities = _dedupe([*target.entities, *page.entities])

    return RequirementsSpec(
        project_name=next((s.project_name.strip() for s in specs if s.project_name.strip()), ""),
        summary=next((s.summary.strip() for s in specs if s.summary.strip()), ""),
        actors=_dedupe(a for s in specs for a in s.actors),
        entities=list(entities.values())[:MAX_ENTITIES],
        api_endpoints=list(endpoints.values())[:MAX_ENDPOINTS],
        pages=list(pages.values())[:MAX_PAGES],
        non_functional=_dedupe(n for s in specs for n in s.non_functional),
        open_questions=_dedupe(q for s in specs for q in s.open_questions),
    )


# --- Analysis -----------------------------------------------------------------------------


def _short_errors(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()[:5]
    )


async def _extract_spec(chat: ChatFn, system: str, user: str, num_ctx: int) -> RequirementsSpec:
    schema = RequirementsSpec.model_json_schema()
    raw = await chat(system, user, schema, num_ctx)
    try:
        return RequirementsSpec.model_validate_json(raw)
    except ValidationError as exc:
        retry_user = (
            f"{user}\n\nYour previous answer did not match the required JSON schema "
            f"({_short_errors(exc)}). Answer again with valid JSON only."
        )
        raw = await chat(system, retry_user, schema, num_ctx)
        try:
            return RequirementsSpec.model_validate_json(raw)
        except ValidationError as retry_exc:
            raise AnalysisError(
                "Model iki denemede de şemaya uygun bir spesifikasyon üretemedi: "
                + _short_errors(retry_exc)
            ) from retry_exc


async def analyze_document(document: str, chat: ChatFn) -> AnalysisResult:
    text = normalize_document(document)
    if not text:
        raise AnalysisError("Doküman boş.")
    chunks = split_into_chunks(text, max_chunk_chars())
    specs = []
    for index, chunk in enumerate(chunks, start=1):
        system = SYSTEM_PROMPT
        if len(chunks) > 1:
            system += CHUNK_NOTE.format(index=index, total=len(chunks))
        user = f"Requirements document:\n\n{chunk}"
        num_ctx = context_window_for(estimate_tokens(system) + estimate_tokens(user))
        specs.append(await _extract_spec(chat, system, user, num_ctx))
    return AnalysisResult(spec=merge_specs(specs), chunk_count=len(chunks))


# --- Task graph ---------------------------------------------------------------------------


def _groups(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _match_entity(endpoint: Endpoint, entities: list[Entity]) -> Entity | None:
    """Find the entity an endpoint belongs to: by its "entity" field, else by its path."""
    if endpoint.entity:
        for entity in entities:
            if slug(entity.name) == slug(endpoint.entity):
                return entity
    segments = [slug(s) for s in endpoint.path.split("/") if s and not s.startswith("{")]
    for entity in entities:
        key = slug(entity.name)
        if key and any(segment.startswith(key) for segment in segments if segment != "api"):
            return entity
    return None


def _join_names(names: list[str], limit: int = 70) -> str:
    joined = ", ".join(names)
    return joined if len(joined) <= limit else joined[: limit - 1].rstrip(", ") + "…"


def build_task_plan(spec: RequirementsSpec) -> list[dict]:
    """Turn a spec into tasks with dependencies. Tasks are appended after their dependencies."""
    tasks: list[dict] = []

    def add(task_type: str, title: str, description: str, details: dict, depends_on: list[str],
            status: str = "planned", performed_by: str | None = None) -> str:
        key = f"T{len(tasks) + 1}"
        tasks.append({
            "key": key, "type": task_type, "title": title, "description": description,
            "details": details, "depends_on": depends_on, "status": status,
            "performed_by": performed_by,
        })
        return key

    analysis = add(
        "requirements", "Gereksinim analizi",
        f"Doküman analiz edildi: {len(spec.entities)} varlık, {len(spec.api_endpoints)} API ucu, "
        f"{len(spec.pages)} sayfa ve {len(spec.open_questions)} açık soru çıkarıldı.",
        {"actors": spec.actors, "non_functional": spec.non_functional,
         "open_questions": spec.open_questions},
        [], status="done", performed_by="master",
    )

    database = add(
        "database", "Veritabanı şeması (SQLite)",
        "Varlıklar için SQLite tabloları, alanları ve ilişkileri tasarlanır." if spec.entities
        else "Dokümanda veri varlığı bulunamadı; tablolar gereksinimlere göre belirlenir.",
        {"entities": [e.model_dump() for e in spec.entities]}, [analysis],
    )

    by_entity: dict[str, list[Endpoint]] = {}
    unmatched: list[Endpoint] = []
    for endpoint in spec.api_endpoints:
        entity = _match_entity(endpoint, spec.entities)
        if entity is None:
            unmatched.append(endpoint)
        else:
            by_entity.setdefault(slug(entity.name), []).append(endpoint)

    backend: list[str] = []
    for group in _groups(spec.entities, BACKEND_ENTITIES_PER_TASK):
        names = [e.name for e in group]
        endpoints = [ep for e in group for ep in by_entity.get(slug(e.name), [])]
        backend.append(add(
            "backend", f"Backend API: {_join_names(names)}",
            f"{', '.join(names)} için FastAPI uç noktaları ve iş kuralları ({len(endpoints)} uç nokta).",
            {"entities": names, "endpoints": [ep.model_dump() for ep in endpoints]}, [database],
        ))
    if unmatched or not backend:
        backend.append(add(
            "backend", "Backend API: diğer uç noktalar" if backend else "Backend API",
            f"Belirli bir varlığa bağlanmayan {len(unmatched)} uç nokta." if unmatched
            else "Dokümanda uç nokta tanımı bulunamadı; API gereksinimlere göre tasarlanır.",
            {"entities": [], "endpoints": [ep.model_dump() for ep in unmatched]}, [database],
        ))

    frontend: list[str] = []
    for group in _groups(spec.pages, FRONTEND_PAGES_PER_TASK):
        names = [p.name for p in group]
        frontend.append(add(
            "frontend", f"Frontend: {_join_names(names)}",
            f"HTML/CSS/JS arayüz sayfaları: {', '.join(names)}.",
            {"pages": [p.model_dump() for p in group]}, [analysis],
        ))
    if not frontend:
        frontend.append(add(
            "frontend", "Frontend arayüzü",
            "Dokümanda sayfa tanımı bulunamadı; arayüz gereksinimlere göre tasarlanır.",
            {"pages": []}, [analysis],
        ))

    build = backend + frontend
    testing = add(
        "testing", "Otomatik testler",
        "Backend uç noktaları ve arayüz akışları için otomatik testler yazılır ve çalıştırılır.",
        {}, build,
    )
    review = add(
        "review", "Kod incelemesi",
        "Üretilen kod, onu yazan ajandan farklı bir ajan tarafından incelenir.", {}, build,
    )
    integration = add(
        "integration", "Entegrasyon",
        "Frontend, backend ve veritabanı birleştirilir; API sözleşmesi kontrol edilir.",
        {}, [testing, review],
    )
    add("documentation", "Dokümantasyon",
        "Kurulum, kullanım ve API dokümantasyonu hazırlanır.", {}, [integration])

    stages: dict[str, int] = {}
    for task in tasks:
        stages[task["key"]] = 1 + max((stages[d] for d in task["depends_on"]), default=0)
        task["stage"] = stages[task["key"]]
    return tasks
