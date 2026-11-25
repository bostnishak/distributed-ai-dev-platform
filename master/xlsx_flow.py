"""Excel requests: the model designs the workbook (sheets, formulas, chart) for the request; no fixed layout is reused."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import deliverable_score
import json_repair
import xlsx_builder
from prompt_loader import load_prompt

MAX_ATTEMPTS = 2
NO_CONTENT = "Excel dosyasının içeriğini üretemedim (model geçerli bir çalışma kitabı döndürmedi). Boş ya da kalıp bir dosya vermemek için oluşturmadım; lütfen tekrar dener misin? Ne için kullanacağını kısaca yazarsan sonuç daha iyi olur."


async def generate(prompt: str, target_lang: str, model: str, out_path: Path) -> dict[str, Any]:
    """Quality loop: build, score, and when the score is below target retry once with the concrete problems; the best attempt is kept."""
    import gateway

    schema = load_prompt("b3_xlsx_schema.txt").replace("{target_lang}", target_lang).replace("{today}", datetime.now(UTC).strftime("%d.%m.%Y"))
    best: tuple[dict[str, Any], int] | None = None
    extra = ""
    for _ in range(MAX_ATTEMPTS):
        res = await gateway.default_client.chat([{"role": "system", "content": schema}, {"role": "user", "content": prompt + extra}], model=model, profile="factual", num_predict=3500, timeout_s=300.0, feature="document_factory", max_retries=1)
        spec = xlsx_builder.parse_spec(json_repair.loads_top(res.content), prompt)
        if spec is None:
            continue
        score, issues = deliverable_score.score_workbook(spec, prompt)
        if best is None or score > best[1]:
            best = (spec, score)
        if best[1] >= deliverable_score.TARGET:
            break
        extra = deliverable_score.feedback(issues)
    if best is None:
        raise RuntimeError(NO_CONTENT)
    spec = best[0]
    xlsx_builder.build_workbook(out_path, spec)
    first = spec["sheets"][0]
    return {
        "file_id": out_path.stem, "format": "xlsx", "title": spec["title"], "summary": spec["description"], "sections": [],
        "table_headers": first["headers"], "table_rows": first["rows"][:12],
        "model": model, "url": f"/api/assistant/media/{out_path.name}", "quality_score": best[1],
    }
