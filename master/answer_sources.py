"""Source handling for grounded answers: the reference list is written by code, never by the model.

* With sources: the model's own "Kaynaklar" section (often shortened or invented) is removed and replaced by the real list of the
  sources that were cited ([S1] ...); if nothing was cited, all provided sources are listed.
* Without sources: citation markers are removed and a plain honesty note is added; no fake "[S1]" entry is ever created.
"""

from __future__ import annotations

import re

_SECTION_RE = re.compile(r"\n+#{1,4}\s*(?:Kaynaklar|Kaynakça|Sources|References)\b.*\Z", re.IGNORECASE | re.DOTALL)
_CITE_RE = re.compile(r"\[S(\d+)\]")
NO_SOURCE_NOTE = "> Not: Bu konuda alıntılanabilir bir kaynak bulunamadı; yukarıdaki bilgiler genel bilgidir ve doğrulanmamıştır. Güncel ve kesin veriler için resmî kurumların yayınlarına bakın."


def finalize(text: str, sources: list[dict[str, str]], grounded: bool) -> str:
    """Return the answer with an authoritative reference list (or an honesty note) appended."""
    if not grounded and not sources:
        return text
    body = _SECTION_RE.sub("", text).rstrip()
    if not sources:
        return f"{_CITE_RE.sub('', body).rstrip()}\n\n{NO_SOURCE_NOTE}"
    ids = {f"S{m}" for m in _CITE_RE.findall(body)}
    shown = [s for s in sources if s["id"] in ids] or sources
    lines = "\n".join(f"- [{s['id']}] {s['title']} — {s['url']}" for s in shown)
    return f"{body}\n\n### Kaynaklar\n{lines}"
