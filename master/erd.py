"""Mermaid ER diagram generated from the real schema (DAT-04), so the diagram cannot drift from the database.

``python master/erd.py`` rewrites docs/plan-v2/erd.md; a test fails when the committed file is out of date.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

import ownership

HEADER = "# Veri modeli (ERD)\n\nBu dosya `python master/erd.py` ile şemadan üretilir; elle değiştirilmez.\n\n"


def _kind(table: str) -> str:
    if table in ownership.OWNED:
        return f"sahip: {ownership.OWNED[table]}"
    if table in ownership.CHILDREN:
        return f"{ownership.CHILDREN[table][1]} altında"
    return "ortak"


def render(conn: sqlite3.Connection) -> str:
    tables = sorted(t for t in ownership.table_names(conn) if t != "search_index" and not t.endswith("_fts"))
    lines = ["```mermaid", "erDiagram"]
    relations: list[str] = []
    for table in tables:
        lines.append(f"    {table} {{")
        for _cid, name, ctype, notnull, _default, pk in conn.execute(f'PRAGMA table_info("{table}")'):
            marks = []
            if pk:
                marks.append("PK")
            fks = {row[3] for row in conn.execute(f'PRAGMA foreign_key_list("{table}")')}
            if name in fks:
                marks.append("FK")
            comment = ""
            if table in ownership.OWNED and name == ownership.OWNED[table]:
                comment = ' "sahip"'
            lines.append(f"        {(ctype or 'TEXT').split('(')[0].lower() or 'text'} {name} {','.join(marks)}{comment}".rstrip())
        lines.append("    }")
        for row in conn.execute(f'PRAGMA foreign_key_list("{table}")'):
            relations.append(f'    {row[2]} ||--o{{ {table} : "{row[3]}"')
    lines += sorted(set(relations))
    lines.append("```")
    legend = ["", "| Tablo | Sınıf |", "|---|---|"] + [f"| {t} | {_kind(t)} |" for t in tables]
    return HEADER + "\n".join(lines) + "\n" + "\n".join(legend) + "\n"


def build() -> str:
    """Create a scratch database with every module's tables and render it."""
    import config

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        root = Path(scratch)
        saved = (config.DB_PATH, config.DATA_DIR, config.UNIFIED_DB)
        config.DB_PATH, config.DATA_DIR, config.UNIFIED_DB = root / "platform.db", root, True
        try:
            import cmm_closed_loop
            import db
            import dbconn
            import hybrid_graph_rag
            import memory_engine
            import user_profile

            db.init_db()
            user_profile.init_db()
            memory_engine.init_memory_db()
            hybrid_graph_rag.HybridGraphRAG()
            cmm_closed_loop.init_cmm_quality_db()
            with dbconn.connection(config.DB_PATH) as conn:
                return render(conn)
        finally:
            config.DB_PATH, config.DATA_DIR, config.UNIFIED_DB = saved


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "docs" / "plan-v2" / "erd.md"
    target.write_text(build(), encoding="utf-8")
    print(f"yazıldı: {target}")
