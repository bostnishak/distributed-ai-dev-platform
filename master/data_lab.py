"""Questions about a CSV are answered by running real SQL (DuckDB), not by the model doing arithmetic.

The model writes one SELECT; it runs in an in-memory database with file and network access disabled, and the rows are
placed next to the question as verified facts.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel, ValidationError

import gateway
import llm
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)
_BANNED_RE = re.compile(r"\b(?:insert|update|delete|drop|create|alter|attach|copy|install|load|pragma|set|export|import|read_\w+|call)\b", re.IGNORECASE)
_MAX_ROWS = 20


class Query(BaseModel):
    sql: str = ""


def run_select(csv_text: str, sql: str) -> tuple[list[str], list[tuple]]:
    """Columns and rows of one read-only SELECT over the table `veri`; ValueError for anything else."""
    import duckdb

    statement = sql.strip().rstrip(";")
    if not statement.lower().startswith(("select", "with")) or ";" in statement or _BANNED_RE.search(statement):
        raise ValueError("yalnızca tek bir SELECT sorgusu çalıştırılır")
    with tempfile.TemporaryDirectory(prefix="cm6453_data_") as tmp:
        source = Path(tmp) / "veri.csv"
        source.write_text(csv_text, encoding="utf-8")
        conn = duckdb.connect(":memory:")
        try:
            conn.execute("CREATE TABLE veri AS SELECT * FROM read_csv_auto(?, header=true)", [str(source)])
            conn.execute("SET enable_external_access = false")
            cursor = conn.execute(statement)
            return [d[0] for d in cursor.description], cursor.fetchmany(_MAX_ROWS)
        except duckdb.Error as exc:
            raise ValueError(str(exc).splitlines()[0]) from exc
        finally:
            conn.close()


async def _write_sql(system: str, user: str, schema: dict) -> str:
    try:
        res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model="qwen3.5:9b",
                                                profile="extract", format_schema=schema, num_predict=500, num_ctx=6144, timeout_s=180.0, feature="data_lab", max_retries=0)
    except Exception as exc:
        raise llm.LLMError(str(exc)) from exc
    return res.content


async def verified_facts(prompt: str, filename: str, text: str, chat: Callable[[str, str, dict], Awaitable[str]] | None = None) -> str:
    """A block with the query and its real result, or an empty string when it does not apply."""
    if not filename.lower().endswith(".csv") or text.count("\n") < 2:
        return ""
    sample = "\n".join(text.splitlines()[:6])
    ask = f"SORU: {prompt[:600]}\n\nTABLO `veri` (ilk satırlar):\n{sample}"
    error = ""
    for _ in range(2):
        try:
            sql = Query.model_validate(json.loads(await (chat or _write_sql)(load_prompt("agent_sql.md"), ask + error, Query.model_json_schema()))).sql
            columns, rows = run_select(text, sql)
        except (llm.LLMError, ValidationError, ImportError, OSError) as exc:
            _log.warning("Veri sorgusu yapılamadı: %s", exc)
            return ""
        except ValueError as exc:
            error = f"\n\nÖnceki sorgu hata verdi: {exc}. Düzelt."
            continue
        table = "\n".join(" | ".join(str(v) for v in row) for row in [columns, *rows])
        return f"\n\n--- DOĞRULANMIŞ HESAP (DuckDB'de çalıştırıldı; sayıları buradan al, kendin hesaplama) ---\nSQL: {sql}\n{table}\n"
    return ""
