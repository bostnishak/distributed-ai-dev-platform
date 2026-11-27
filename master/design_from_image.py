"""Screenshot or sketch to a working page.

Colours are measured from the pixels, layout and texts are read by the local vision model, the page is generated with
the normal checks, and the result is rendered and compared with the picture. The similarity figures are reported as
measured; they are not claimed to mean "identical".
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import subprocess

import httpx
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from gateway import local_gpu
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)
_TRIGGER_RE = re.compile(r"koda\s+(?:çevir|dök|dönüştür)|(?:bu|şu)\s+(?:tasarım|ekran|arayüz|taslağ|görsel)\w*\s*.{0,40}?(?:yap|kodla|uygula|oluştur)|screenshot\s+to\s+code|turn\s+this\s+into\s+(?:html|code)|aynısını\s+(?:yap|kodla)", re.IGNORECASE)
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
_MAX_BYTES = 8_000_000


class Region(BaseModel):
    name: str = ""
    elements: list[str] = Field(default_factory=list)


class Screen(BaseModel):
    title: str = ""
    layout: str = ""
    regions: list[Region] = Field(default_factory=list)
    texts: list[str] = Field(default_factory=list)


def wants_code(prompt: str, filename: str) -> bool:
    return filename.lower().endswith(_IMAGE_EXT) and bool(_TRIGGER_RE.search(prompt))


def _png(raw: bytes) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(raw)).convert("RGB")
    image.thumbnail((1280, 1280))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _load(raw: bytes, width: int = 320):
    """The picture scaled without blending neighbouring colours, so flat colours stay exact."""
    from PIL import Image

    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if image.width > width:
        image = image.resize((width, max(round(image.height * width / image.width), 1)), Image.Resampling.NEAREST)
    return image


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _near(first: tuple[int, ...], second: tuple[int, ...], limit: int = 24) -> bool:
    return sum(abs(a - b) for a, b in zip(first, second, strict=True)) < limit


def palette(raw: bytes, count: int = 6) -> list[tuple[str, float]]:
    """(hex colour, share of the picture), most used first. Anti-aliasing shades merge into the colour they belong to."""
    image = _load(raw)
    total = image.width * image.height
    found: list[list] = []
    for pixels, rgb in sorted(image.getcolors(total), reverse=True):
        near = next((entry for entry in found if _near(rgb, entry[0])), None)
        if near is None:
            found.append([rgb, pixels])
        else:
            near[1] += pixels
    found.sort(key=lambda entry: -entry[1])
    vivid = [e for e in found[count:] if max(e[0]) - min(e[0]) > 80 and e[1] / total >= 0.005]  # small accents such as buttons matter
    return [(_hex(rgb), round(pixels / total, 3)) for rgb, pixels in [*found[:count], *vivid[:2]] if pixels / total >= 0.005]


def bands(raw: bytes) -> list[tuple[int, int, str]]:
    """Full-width horizontal strips as (from %, to %, background colour)."""
    image = _load(raw, 200)
    pixels = image.load()
    rows = []
    for y in range(image.height):
        edge = [pixels[x, y] for x in (0, 1, 2, image.width - 3, image.width - 2, image.width - 1)]
        rows.append(max(set(edge), key=edge.count))
    out: list[list] = []
    for y, rgb in enumerate(rows):
        if out and _near(rgb, out[-1][2]):
            out[-1][1] = y + 1
        else:
            out.append([y, y + 1, rgb])
    return [(round(100 * a / image.height), round(100 * b / image.height), _hex(rgb)) for a, b, rgb in out if (b - a) / image.height >= 0.03]


def blocks(raw: bytes, colours: list[tuple[str, float]], limit: int = 8) -> list[dict]:
    """Solid rectangles (buttons, panels) of each non-background colour: position and size in percent."""
    image = _load(raw, 160)
    width, height = image.size
    pixels = image.load()
    found: list[dict] = []
    for hex_, _share in colours[1:]:
        target = tuple(int(hex_[i : i + 2], 16) for i in (1, 3, 5))
        todo = {(x, y) for y in range(height) for x in range(width) if _near(pixels[x, y], target)}
        while todo:
            stack = [todo.pop()]
            xs, ys = [], []
            while stack:
                x, y = stack.pop()
                xs.append(x)
                ys.append(y)
                for step in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if step in todo:
                        todo.remove(step)
                        stack.append(step)
            w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if w >= width * 0.05 and h >= height * 0.03 and len(xs) / (w * h) > 0.6 and w * h < width * height * 0.9:
                found.append({"colour": hex_, "x": round(100 * min(xs) / width), "y": round(100 * min(ys) / height),
                              "w": round(100 * w / width), "h": round(100 * h / height)})
    return sorted(found, key=lambda b: -(b["w"] * b["h"]))[:limit]


def geometry(raw: bytes, colours: list[tuple[str, float]]) -> str:
    lines = [f"- yatay şerit: üstten %{a}-%{b} arası zemin {c}" for a, b, c in bands(raw)]
    lines += [f"- dolgulu kutu: {b['colour']} renkli, soldan %{b['x']}, üstten %{b['y']}, genişlik %{b['w']}, yükseklik %{b['h']}" for b in blocks(raw, colours)]
    return "\n".join(lines)


def _vivid(hex_: str) -> bool:
    channels = [int(hex_[i : i + 2], 16) for i in (1, 3, 5)]
    return max(channels) - min(channels) > 60


def missing_blocks(reference: bytes, shot: bytes) -> list[dict]:
    """Coloured boxes of the picture (buttons, badges) that have no box of that colour nearby in the rendered page."""
    colours = palette(reference)
    wanted = [b for b in blocks(reference, colours) if _vivid(b["colour"])]
    seen = blocks(shot, [colours[0], *[(b["colour"], 0.0) for b in wanted]], limit=40) if wanted else []
    return [b for b in wanted if not any(s["colour"] == b["colour"] and abs(s["x"] - b["x"]) <= 30 and abs(s["y"] - b["y"]) <= 30 for s in seen)]


async def _fix_blocks(ws_id: str, absent: list[dict]) -> None:
    import workspace_builder as wb

    wanted = "; ".join(f"soldan %{b['x']}, üstten %{b['y']} konumundaki düğme/kutunun arka plan rengi {b['colour']} olmalı" for b in absent[:3])
    async for _event in wb.stream_iterate_project(ws_id, f"Yalnız şu renkleri düzelt, başka hiçbir şeyi değiştirme: {wanted}."):
        pass


def similarity(first: bytes, second: bytes) -> tuple[int, int]:
    """(layout, colour) similarity in percent: block brightness structure, and overlap of the colour histograms."""
    from PIL import Image

    images = [Image.open(io.BytesIO(raw)).convert("RGB") for raw in (first, second)]
    grids = [list(i.convert("L").resize((24, 24)).getdata()) for i in images]
    means = [sum(g) / len(g) for g in grids]
    top = sum((a - means[0]) * (b - means[1]) for a, b in zip(*grids, strict=True))
    bottom = (sum((a - means[0]) ** 2 for a in grids[0]) * sum((b - means[1]) ** 2 for b in grids[1])) ** 0.5
    layout = max(top / bottom, 0.0) if bottom else float(abs(means[0] - means[1]) < 8)
    histograms = []
    for image in images:
        counts: dict[tuple[int, int, int], int] = {}
        for r, g, b in image.resize((64, 64)).getdata():
            key = (r // 48, g // 48, b // 48)
            counts[key] = counts.get(key, 0) + 1
        histograms.append(counts)
    colour = sum(min(n, histograms[1].get(k, 0)) for k, n in histograms[0].items()) / (64 * 64)
    return round(layout * 100), round(colour * 100)


def build_request(prompt: str, colours: list[tuple[str, float]], screen: Screen, measured: str = "") -> str:
    regions = "\n".join(f"- {r.name}: {'; '.join(r.elements)}" for r in screen.regions[:10])
    texts = ", ".join(f'"{t}"' for t in screen.texts[:30])
    shades = ", ".join(f"{hex_} (%{round(share * 100)})" for hex_, share in colours)
    return (
        "Ekran görüntüsündeki arayüzü tek HTML dosyası olarak birebir yeniden oluştur.\n"
        f"Kullanıcının isteği: {prompt.strip()}\n\nÖlçülen renkler (yalnız bunları kullan): {shades}\n"
        f"Piksellerden ölçülen yerleşim (kesin; her rengi burada görüldüğü yerde kullan):\n{measured}\n"
        f"En geniş alanı kaplayan {colours[0][0] if colours else '#ffffff'} arka plan rengidir.\n"
        f"Başlık: {screen.title}\nYerleşim: {screen.layout}\nBölgeler:\n{regions}\nGörünen metinler (aynen kullan): {texts}\n"
        "Görselde olmayan bölüm, örnek veri ya da yer tutucu (placeholder) metin ekleme."
    )


async def read_screen(png: bytes) -> Screen:
    answer = await local_gpu.look(load_prompt("agent_screen_reader.md"), png, Screen.model_json_schema())
    return Screen.model_validate(json.loads(answer))


async def _stream(prompt: str, raw: bytes):
    import assistant_stream_fastpaths as fp
    import project_flow
    import vlm_critique
    import workspace_builder as wb

    try:
        png = _png(raw)
        colours = palette(png)
        yield fp.sse_event({"type": "token", "content": f"Görselden ölçülen renkler: {', '.join(c for c, _ in colours)}\nYerleşim görsel modelle okunuyor...\n"})
        screen = await read_screen(png)
        yield fp.sse_event({"type": "token", "content": f"Okunan bölgeler: {', '.join(r.name for r in screen.regions) or 'bulunamadı'}\n"})
        done = None
        async for evt in project_flow.stream_generate(build_request(prompt, colours, screen, geometry(png, colours)), project_type="web"):
            if message := fp._format_project_evt(evt):
                yield fp.sse_event({"type": "token", "content": message})
            if evt.get("type") == "done":
                done = evt
        if done is None:
            raise RuntimeError("Sayfa üretilemedi.")
        page = wb.safe_workspace_dir(done["workspace"]["id"]) / "index.html"
        if page.is_file():
            from PIL import Image

            width, height = Image.open(io.BytesIO(png)).size
            size = (max(width, 320), max(height, 320))
            shot = await asyncio.to_thread(vlm_critique.screenshot, page, *size)
            if absent := missing_blocks(png, shot):
                yield fp.sse_event({"type": "token", "content": f"\nGörseldeki renkli alan(lar) sayfada yok ({', '.join(b['colour'] for b in absent)}); düzeltiliyor...\n"})
                await _fix_blocks(done["workspace"]["id"], absent)
                shot = await asyncio.to_thread(vlm_critique.screenshot, page, *size)
                if left := missing_blocks(png, shot):
                    yield fp.sse_event({"type": "token", "content": f"UYARI: şu renkli alanlar hâlâ görseldeki gibi değil: {', '.join(b['colour'] for b in left)}.\n"})
            layout, colour = similarity(png, shot)
            yield fp.sse_event({"type": "token", "content": f"\nÖlçülen benzerlik — yerleşim: %{layout}, renk dağılımı: %{colour}. Önizlemeyi görselle karşılaştır.\n"})
        _failed, notes = fp._verdict(done)
        yield fp.sse_event({"type": "token", "content": "".join(notes)})
        yield fp.sse_event(fp._attach_workspace_flags(wb, done["workspace"], done["tree"]))
        yield fp.sse_event({"type": "done", "model": "screen-to-code", "task_type": "proje"})
    except (ImportError, OSError, RuntimeError, ValueError, ValidationError, httpx.HTTPError, subprocess.SubprocessError, KeyError) as exc:
        _log.warning("screen to code failed: %r", exc)
        yield fp.sse_event({"type": "error", "content": f"Görselden koda çevirme tamamlanamadı: {exc}"})


def fastpath(prompt: str, file: UploadFile | None) -> StreamingResponse | None:
    if file is None or not wants_code(prompt, file.filename or ""):
        return None
    raw = file.file.read(_MAX_BYTES + 1)  # read now: the upload is closed once the request handler returns
    file.file.seek(0)
    if not raw or len(raw) > _MAX_BYTES:
        return None
    return StreamingResponse(_stream(prompt, raw), media_type="text/event-stream")
