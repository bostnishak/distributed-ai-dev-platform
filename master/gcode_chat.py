"""Chat side of G-code requests: read the numbers from the request, generate and check the program, answer with setup sheet and file."""

from __future__ import annotations

import re
import uuid
from typing import Any

import gcode_gen as gg
import json_repair
from gcode_job import build_job
from prompt_loader import load_prompt

_REQUEST_RE = re.compile(
    r"(g[\s-]?code|gkod|nc\s+kod\w*|cnc\s+(?:freze|program|kod|tezgah|işleme)\w*|işleme\s+programı|freze\s+programı|freze\s+için\s+program)", re.IGNORECASE
)
_VERB_RE = re.compile(r"\b(yaz\w*|üret\w*|hazırla\w*|oluştur\w*|çıkar\w*|ver\b|verir\w*|generate|write|create)\b", re.IGNORECASE)
_OP_TITLES = {
    "face": "Yüzey frezeleme", "holes": "Delik", "pocket": "Dikdörtgen cep", "round_pocket": "Dairesel cep", "slot": "Yuva",
    "profile": "Dış kontur", "engrave": "Kazıma (şekil)",
}


def is_gcode_request(prompt: str, has_file: bool) -> bool:
    return not has_file and bool(_REQUEST_RE.search(prompt)) and bool(_VERB_RE.search(prompt))


_PATTERNS = {"corners": "köşe", "corner": "köşe", "grid": "ızgara", "circle": "daire (bolt circle)", "bolt_circle": "daire (bolt circle)", "line": "sıra", "row": "sıra", "center": "merkez"}


def _num(op: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = op.get(key)
    return float(value) if isinstance(value, (int, float)) else default


def _depth(op: dict[str, Any]) -> str:
    return f"derinlik {_num(op, 'depth', 0.5):g} mm"


def _holes(op: dict[str, Any]) -> str:
    pattern = _PATTERNS.get(str(op.get("pattern")).lower(), op.get("pattern"))
    where = f"{pattern} deseni" if op.get("pattern") else f"{len(op.get('points') or [])} nokta"
    return f"Ø{_num(op, 'diameter'):g} mm, {where}, " + ("delik boydan boya" if op.get("through", True) else _depth(op))


_DETAIL = {
    "face": _depth,
    "holes": _holes,
    "pocket": lambda o: f"{_num(o, 'width'):g}x{_num(o, 'length'):g} mm, {_depth(o)}",
    "round_pocket": lambda o: f"Ø{_num(o, 'diameter'):g} mm, {_depth(o)}",
    "slot": lambda o: f"{_num(o, 'width'):g} mm genişlik, {_num(o, 'length'):g} mm uzunluk, {_depth(o)}",
    "profile": lambda o: (f"Ø{_num(o, 'diameter'):g} mm daire" if o.get("shape") == "circle" else "dikdörtgen") + f", {_depth(o)}",
    "engrave": lambda o: f"{o.get('shape') or 'daire'}, {_depth(o)}",
}


def _op_line(op: dict[str, Any]) -> str:
    k = str(op.get("type", ""))
    return f"- {_OP_TITLES.get(k, k)}: {_DETAIL.get(k, lambda _o: '')(op)}"


def render_answer(job: gg.Job, prog: gg.Program, url: str) -> str:
    mat = gg.MATERIALS[job.material]
    sx, sy, sz = job.stock
    tools = "\n".join(f"| T{t['no']} | {t['name']} | {t['rpm']} | {t['feed']} | {'Matkap' if t['kind'] == 'drill' else 'Freze'} |" for t in prog.tools)
    st = prog.stats
    shown = "\n".join(prog.lines) if len(prog.lines) <= 140 else "\n".join(prog.lines[:140]) + "\n( ... devamı dosyada ... )"
    warn = "".join(f"\n- ⚠ {w}" for w in prog.warnings)
    assumed = "\n**Varsayımlar** (istekte yoktu; farklıysa söyle, programı yeniden üreteyim):\n" + "\n".join(f"- {a}" for a in job.assumptions) + "\n" if job.assumptions else ""
    unit = "G20 inç" if job.units == "inch" else "G21 mm"
    ops = "\n".join(_op_line(op) for op in job.ops)
    return (
        f"## CNC freze programı — {mat['name']} {sx:g}x{sy:g}x{sz:g} mm\n\n"
        f"- **Sıfır noktası:** X0 Y0 = parçanın sol alt köşesi, Z0 = parça üst yüzeyi · **Birim:** {unit} · **Dil:** {job.flavor.upper()}\n"
        f"- **Kesme parametreleri** malzeme tablosundan hesaplandı (Vc, diş başı ilerleme, devir); tahmini işleme süresi **{st['minutes']} dk**, "
        f"kesme yolu {st['cut_mm']} mm.\n\n**İşlemler (programdaki sıraya göre değil, istenenler):**\n{ops}\n\n"
        f"| Takım | Tanım | Devir (dev/dk) | İlerleme (mm/dk) | Tür |\n|---|---|---|---|---|\n{tools}\n\n"
        f"[G-code dosyasını indir (.nc)]({url})\n\n```gcode\n{shown}\n```\n"
        f"\n**Kontroller (mm):** takım yolu sınırları X {st['bounds'][0]}…{st['bounds'][2]}, Y {st['bounds'][1]}…{st['bounds'][3]}; en derin Z {st['min_z']} mm."
        f"{warn}\n{assumed}\n> Gerçek tezgâhta çalıştırmadan önce simülatörde doğrula; sıfır noktasını, bağlama ve takım boyunu kendi tezgâhına göre ayarla."
    )


async def generate(prompt: str, llm_json: Any, media_dir: Any) -> tuple[str, str]:
    """(markdown answer, model note). `llm_json(system, user)` returns the parsed parameter JSON or None."""
    raw = await llm_json(load_prompt("b3_gcode_params.txt"), prompt)
    if not raw:
        return "İsteğini sayısal ölçülere çeviremedim; parça ölçülerini, malzemeyi ve yapılacak işlemleri (delik, cep, yuva, kontur) yazar mısın?", "gcode-params"
    job, question = build_job(raw, prompt)
    if job is None:
        return question, "gcode-clarify"
    prog = gg.generate(job)
    name = f"gcode-{uuid.uuid4().hex[:8]}.nc"
    (media_dir / name).write_text("\n".join(prog.lines) + "\n", encoding="utf-8")
    return render_answer(job, prog, f"/api/assistant/media/{name}"), "gcode-generator"


async def fastpath(prompt: str, has_file: bool) -> Any:
    """SSE response for a G-code request, or None when the prompt is something else."""
    if not is_gcode_request(prompt, has_file):
        return None
    import multimodal_studio as mms
    from assistant_stream_fastpaths import single_token_stream

    model = await mms.pick_best_model("general")

    async def _params(system: str, user: str) -> dict[str, Any] | None:
        """Parameter extraction waits for the shared model (up to 3 min) instead of giving up after 35 s."""
        import gateway

        for _ in range(2):
            try:
                res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model=model, profile="factual", num_predict=800, timeout_s=180.0, feature="gcode_params", max_retries=0)
            except (OSError, RuntimeError, ValueError, TypeError):
                continue
            if parsed := json_repair.loads_top(res.content):
                return parsed
        return None

    answer, tag = await generate(prompt, _params, mms.media_dir())
    return single_token_stream(answer, tag, "cnc")
