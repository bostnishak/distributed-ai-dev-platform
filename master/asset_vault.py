"""Generated pages must work with the network cut: CDN links become copies from the local vault.

A known library or font link is rewritten to a file copied into the project's `vendor/` folder (so the preview and the
ZIP export carry it). A link nothing in the vault can stand in for stays and is reported by the zero-CDN gate.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

import config

FOLDER = "vendor"
_SKIP = {".history", ".ai-os", "node_modules", "venv", ".venv", FOLDER}
_TAG_RE = re.compile(r"<(?:script|link|img|iframe|source|audio|video)\b[^>]*?\b(?:src|href)\s*=\s*([\"'])((?:https?:)?//[^\"']+)\1[^>]*>(?:\s*</script>)?", re.IGNORECASE)
_CSS_RE = re.compile(r"@import\s+(?:url\()?\s*([\"']?)((?:https?:)?//[^\"')]+)\1\s*\)?\s*;?|url\(\s*([\"']?)((?:https?:)?//[^\"')]+)\3\s*\)", re.IGNORECASE)
_ESM_RE = re.compile(r"""(?:^|(?<=[>;{}]))[ \t]*import\s+(?:[\w{}*,\s]+\s+from\s+)?["'](https?://[^"']+)["'];?[ \t]*\n?""", re.MULTILINE)
_IGNORED_LINK_RE = re.compile(r"""rel\s*=\s*["'](?:preconnect|dns-prefetch|canonical|author|license|alternate)""", re.IGNORECASE)
# (pattern in the URL, files of the vault in load order, kind); the first match wins
_LIBRARIES = (
    (r"vega-embed", ("vega/build/vega.min.js", "vega-lite/build/vega-lite.min.js", "vega-embed/build/vega-embed.min.js"), "js"),
    (r"vega-lite", ("vega-lite/build/vega-lite.min.js",), "js"),
    (r"(?:/|@)vega(?:@[\d.]+)?(?:/|$)", ("vega/build/vega.min.js",), "js"),
    (r"chart(?:\.js|\.umd)|/Chart\.js/", ("chart.js/dist/chart.umd.min.js",), "js"),
    (r"mermaid", ("mermaid/dist/mermaid.min.js",), "js"),
    (r"katex[^?#]*\.css", ("katex/dist/katex.min.css",), "css"),
    (r"katex[^?#]*\.js|katex(?:@[\d.]+)?$", ("katex/dist/katex.min.js",), "js"),
    (r"cytoscape", ("cytoscape/dist/cytoscape.min.js",), "js"),
    (r"plotly", ("plotly.js-basic-dist-min/plotly-basic.min.js",), "js"),
)
_FONTS = {"inter": "fontsource-inter", "jetbrains mono": "fontsource-jetbrains-mono", "plus jakarta sans": "fontsource-plus-jakarta-sans"}
_RANGES = {"latin": "U+0000-00FF,U+2018-201F,U+20AC", "latin-ext": "U+0100-02AF,U+1E00-1EFF,U+20A0-20C0"}  # latin-ext carries ğ ş İ ı
_log = logging.getLogger(__name__)


def source() -> Path:
    own = config.data_dir() / "vendor" / "lib"
    return own if own.is_dir() else Path(__file__).resolve().parent / "data" / "vendor" / "lib"


def _files(ws_dir: Path) -> list[Path]:
    return [p for p in sorted(ws_dir.rglob("*")) if p.suffix.lower() in (".html", ".htm", ".css", ".js") and p.is_file() and not _SKIP & set(p.relative_to(ws_dir).parts)]


def _copy(ws_dir: Path, part: str) -> str:
    """Copies one vault file (and the fonts beside a stylesheet) into the project; returns its project path."""
    origin, target = source() / part, ws_dir / FOLDER / part
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origin, target)
    if part.endswith("katex.min.css"):
        shutil.copytree(origin.parent / "fonts", target.parent / "fonts", dirs_exist_ok=True)
    return f"{FOLDER}/{part}"


def _font_css(ws_dir: Path, url: str) -> str:
    """The stylesheet that stands in for a Google Fonts link; "" when no requested family is in the vault."""
    wanted = [family for family in _FONTS if re.search(rf"family=[^&]*{family.replace(' ', r'(?:\+|%20| )')}\b", url, re.IGNORECASE)]
    rules = []
    for family in wanted:
        folder = source() / _FONTS[family] / "files"
        for font in sorted(folder.glob("*.woff2")):
            match = re.search(r"-(latin-ext|latin)-(\d00)-normal$", font.stem)
            if match:
                subset, weight = match.groups()
                _copy(ws_dir, f"{_FONTS[family]}/files/{font.name}")
                rules.append(f"@font-face{{font-family:'{family.title()}';font-style:normal;font-weight:{weight};font-display:swap;src:url({_FONTS[family]}/files/{font.name}) format('woff2');unicode-range:{_RANGES[subset]}}}")
    if not rules:
        return ""
    name = "fonts-" + "-".join(f.replace(" ", "") for f in wanted) + ".css"
    (ws_dir / FOLDER / name).write_text("\n".join(rules) + "\n", encoding="utf-8")
    return f"{FOLDER}/{name}"


def _local(ws_dir: Path, url: str) -> list[tuple[str, str]]:
    """[(project path, "js"|"css")] standing in for the URL; [] when the vault has nothing for it."""
    try:
        if "fonts.googleapis.com" in url:
            made = _font_css(ws_dir, url)
            return [(made, "css")] if made else []
        for pattern, parts, kind in _LIBRARIES:
            if re.search(pattern, url.split("?")[0], re.IGNORECASE):
                return [(_copy(ws_dir, part), kind) for part in parts]
    except OSError as exc:
        _log.warning("kasadan kopyalanamadı (%s): %s", url, exc)
    return []


def _element(path: str, kind: str, up: str) -> str:
    return f'<link rel="stylesheet" href="{up}{path}">' if kind == "css" else f'<script src="{up}{path}"></script>'


_ICON_RE = re.compile(r"<(i|span)\b([^>]*?)\bdata-lucide=([\"'])([a-z0-9-]+)\3([^>]*)></\1>", re.IGNORECASE)
_LUCIDE_SCRIPT_RE = re.compile(r"<script\b[^>]*\bsrc=[\"'][^\"']*lucide[^\"']*[\"'][^>]*>\s*</script>|<script\b[^>]*>\s*lucide\.createIcons\([^)]*\);?\s*</script>", re.IGNORECASE)
_LUCIDE_CALL_RE = re.compile(r"(?<![\w.])(?:window\.)?lucide\.createIcons\([^()]*\);?")


def _symbol(sprite: str, name: str) -> tuple[str, str]:
    """(viewBox, shapes) of one symbol, following the `<use href="#other">` aliases of renamed icons."""
    for _hop in range(3):
        found = re.search(rf'<symbol id="{re.escape(name)}" viewBox="([^"]+)">(.*?)</symbol>', sprite, re.DOTALL)
        if not found:
            break
        alias = re.fullmatch(r'<use href="#([a-z0-9-]+)"\s*/>', found.group(2).strip())
        if not alias:
            return found.group(1), re.sub(r">\s+<", "><", found.group(2).strip())
        name = alias.group(1)
    return "", ""


def icon(name: str, attributes: str = "") -> str:
    """The inline SVG of one Lucide icon from the vault; "" when there is no such icon."""
    try:
        box, body = _symbol((source() / "lucide-static" / "sprite.svg").read_text(encoding="utf-8"), name)
    except OSError:
        return ""
    if not body:
        return ""
    extra = f" {attributes.strip()}" if attributes.strip() else ""
    return (f'<svg{extra} width="1em" height="1em" viewBox="{box}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')


def _inline_icons(text: str, done: list[str]) -> str:
    """`<i data-lucide="x">` placeholders become the SVG itself; the icon script is dropped when nothing needs it."""
    missing: list[str] = []

    def swap(match: re.Match) -> str:
        made = icon(match.group(4), (match.group(2) + match.group(5)).rstrip())
        if made:
            done.append(f"lucide:{match.group(4)}")
            return made
        missing.append(match.group(4))
        return match.group(0)

    changed = _ICON_RE.sub(swap, text)
    if changed != text and not missing and "data-lucide" not in changed:
        changed = _LUCIDE_CALL_RE.sub("", _LUCIDE_SCRIPT_RE.sub("", changed))
    return changed


def _rewrite_html(ws_dir: Path, text: str, up: str, done: list[str]) -> str:
    def tag(match: re.Match) -> str:
        if _IGNORED_LINK_RE.search(match.group(0)):
            return ""  # a hint to a server that will never be called
        found = _local(ws_dir, match.group(2))
        if not found:
            return match.group(0)
        done.append(match.group(2))
        return "".join(_element(path, kind, up) for path, kind in found)

    modules: list[str] = []

    def module(match: re.Match) -> str:
        found = _local(ws_dir, match.group(1))
        if not found:
            return match.group(0)
        done.append(match.group(1))
        modules.extend(_element(path, kind, up) for path, kind in found)
        return ""  # the library's global takes the place of the imported name

    text = _ESM_RE.sub(module, _TAG_RE.sub(tag, text))
    if modules:
        head = "".join(dict.fromkeys(modules))
        text = text.replace("</head>", head + "</head>", 1) if "</head>" in text else head + text
    return text


def _rewrite_css(ws_dir: Path, text: str, up: str, done: list[str]) -> str:
    def rule(match: re.Match) -> str:
        url = match.group(2) or match.group(4)
        found = _local(ws_dir, url) if match.group(2) else []
        if not found:
            return match.group(0)
        done.append(url)
        return "".join(f'@import url("{up}{path}");' for path, kind in found if kind == "css")

    return _CSS_RE.sub(rule, text)


def localize(ws_dir: Path) -> list[str]:
    """Rewrites every link the vault can serve; returns the URLs that were replaced."""
    done: list[str] = []
    for path in _files(ws_dir):
        if path.suffix.lower() == ".js":
            continue
        up = "../" * (len(path.relative_to(ws_dir).parts) - 1)
        text = path.read_text(encoding="utf-8", errors="replace")
        page = text if path.suffix.lower() == ".css" else _rewrite_html(ws_dir, _inline_icons(text, done), up, done)
        changed = _rewrite_css(ws_dir, page, up, done)
        if changed != text:
            path.write_text(changed, encoding="utf-8")
    return list(dict.fromkeys(done))


def external(ws_dir: Path) -> list[str]:
    """Files the pages would still fetch from the internet."""
    found = []
    for path in _files(ws_dir):
        text, name = path.read_text(encoding="utf-8", errors="replace"), path.relative_to(ws_dir).as_posix()
        urls = [m.group(2) for m in _TAG_RE.finditer(text) if not _IGNORED_LINK_RE.search(m.group(0))] if path.suffix.lower() != ".js" else []
        urls += [m.group(2) or m.group(4) for m in _CSS_RE.finditer(text)] if path.suffix.lower() != ".js" else []
        urls += _ESM_RE.findall(text)
        found += [f"{name}: {url[:140]}" for url in urls]
    return list(dict.fromkeys(found))


def blocking(ws_dir: Path, request: str = "") -> list[str]:
    """External links the user did not ask for (a link written in the request is their choice)."""
    return [line for line in external(ws_dir) if line.split(": ", 1)[1] not in request]
