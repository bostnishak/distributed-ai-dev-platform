"""Projects that share a data contract, changed together or not at all.

"sözleşme bağla: backend, frontend" links workspaces. "alan değiştir: users.name -> full_name" shows every place in
every linked project, and proves the migration on a copy of each real database (up, check the rows, down, compare,
up again). "alan değiştir uygula: ..." then renames in all of them, regenerates TypeScript types, runs their tests and
puts everything back if any step fails. Each project gets its own version snapshot and the migration files.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import config
import sql_safe
import workspace_builder as wb
import workspace_docker

_LINK_RE = re.compile(r"^\s*(?:sözleşme\s+bağla|link\s+contract)\s*:\s*(?P<names>.+)$", re.IGNORECASE)
_RENAME_RE = re.compile(
    r"^\s*alan\s+(?:adını\s+)?değiştir(?P<apply>\s+uygula)?\s*:\s*(?P<table>[A-Za-z_]\w*)\.(?P<old>[A-Za-z_]\w*)\s*(?:->|→|=>)\s*(?P<new>[A-Za-z_]\w*)\s*$", re.IGNORECASE)
_CODE = (".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".sql", ".json", ".yaml", ".yml", ".md")
_DB = (".db", ".sqlite", ".sqlite3")
_TS_TYPES = {"INTEGER": "number", "REAL": "number", "NUMERIC": "number", "TEXT": "string", "BLOB": "Uint8Array", "BOOLEAN": "boolean"}
TYPES_FILE = "contract.types.ts"


def _registry() -> Path:
    return config.data_dir() / "federation.json"


def linked() -> list[str]:
    try:
        ids = json.loads(_registry().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [i for i in ids if wb.safe_workspace_dir(i).is_dir()]


def find_workspace(name: str) -> str:
    """Id of the newest workspace whose id or name matches."""
    wanted = name.strip().casefold()
    for meta in wb.list_workspaces():
        if wanted in (str(meta.get("id", "")).casefold(), str(meta.get("name", "")).casefold()):
            return str(meta["id"])
    return next((str(m["id"]) for m in wb.list_workspaces() if wanted in str(m.get("name", "")).casefold() or wanted in str(m.get("id", "")).casefold()), "")


def link(names: list[str]) -> str:
    ids, missing = [], []
    for name in names:
        found = find_workspace(name)
        (ids if found else missing).append(found or name)
    if missing or len(ids) < 2:
        return f"Bağlanamadı. Bulunamayan: {', '.join(missing) or '-'}. En az iki proje adı yazın."
    _registry().parent.mkdir(parents=True, exist_ok=True)
    _registry().write_text(json.dumps(sorted(set(ids))), encoding="utf-8")
    return "Sözleşme kaydı: " + ", ".join(f"`{i}`" for i in sorted(set(ids)))


def occurrences(ws_dir: Path, name: str) -> list[tuple[str, int, str]]:
    pattern = re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")
    out = []
    for rel in wb.list_relative_files(ws_dir):
        if rel.endswith(_CODE) and not rel.startswith("migrations/") and rel != TYPES_FILE:
            lines = (ws_dir / rel).read_text(encoding="utf-8", errors="replace").splitlines()
            out += [(rel, number, line.strip()[:110]) for number, line in enumerate(lines, 1) if pattern.search(line)]
    return out


def databases(ws_dir: Path, table: str, column: str) -> list[Path]:
    found = []
    for path in ws_dir.rglob("*"):
        if path.suffix not in _DB or ".history" in path.parts or not path.is_file():
            continue
        try:
            with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
                if column in [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]:
                    found.append(path)
        except sqlite3.DatabaseError:
            continue
    return found


def migration(table: str, old: str, new: str) -> tuple[str, str]:
    return (f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}";\n', f'ALTER TABLE "{table}" RENAME COLUMN "{new}" TO "{old}";\n')


def _state(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[tuple]]:
    columns = [r[1] for r in conn.execute(f"PRAGMA table_info({sql_safe.safe_ident(table)})")]
    return columns, conn.execute(sql_safe.build_select(table, order_by="rowid")).fetchall()


def round_trip(database: Path, table: str, old: str, new: str) -> str:
    """Up, down and up again on a copy of the real database; returns the proof line, ValueError when rows differ."""
    up, down = migration(table, old, new)
    with tempfile.TemporaryDirectory(prefix="cm6453_mig_", ignore_cleanup_errors=True) as tmp:
        copy = Path(tmp) / "copy.db"
        with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(copy)) as target:
            source.backup(target)
        with closing(sqlite3.connect(copy)) as conn:
            columns, rows = _state(conn, table)
            conn.executescript(up)
            after_columns, after_rows = _state(conn, table)
            if after_rows != rows or after_columns != [new if c == old else c for c in columns]:
                raise ValueError(f"{database.name}: ileri göç satırları değiştirdi")
            conn.executescript(down)
            if _state(conn, table) != (columns, rows):
                raise ValueError(f"{database.name}: geri göç eski hale döndürmedi")
            conn.executescript(up)
            if _state(conn, table) != (after_columns, after_rows):
                raise ValueError(f"{database.name}: ikinci ileri göç farklı sonuç verdi")
    return f"`{database.name}` kopyasında ileri → geri → ileri: {len(rows)} satır değişmeden kaldı"


def typescript(database: Path) -> str:
    out = []
    with closing(sqlite3.connect(database)) as conn:
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            fields = "\n".join(f"  {r[1]}: {_TS_TYPES.get(str(r[2]).upper(), 'string')}{'' if r[3] or r[5] else ' | null'};" for r in conn.execute(f'PRAGMA table_info("{table}")'))
            out.append(f"export interface {''.join(w.capitalize() for w in table.split('_'))} {{\n{fields}\n}}\n")
    return "\n".join(out)


def _backup(ids: list[str], root: Path) -> None:
    for ws_id in ids:
        shutil.copytree(wb.safe_workspace_dir(ws_id), root / ws_id)


def _restore(ids: list[str], root: Path) -> None:
    for ws_id in ids:
        target = wb.safe_workspace_dir(ws_id)
        for path in sorted(target.rglob("*"), reverse=True):
            if path.is_file() and not (root / ws_id / path.relative_to(target)).exists():
                path.unlink()
        shutil.copytree(root / ws_id, target, dirs_exist_ok=True)


def _rewrite(ws_dir: Path, table: str, old: str, new: str) -> list[str]:
    pattern = re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")
    changed = []
    for rel in sorted({rel for rel, _n, _t in occurrences(ws_dir, old)}):
        path = ws_dir / rel
        path.write_text(pattern.sub(new, path.read_text(encoding="utf-8")), encoding="utf-8")
        changed.append(rel)
    up, down = migration(table, old, new)
    folder = ws_dir / "migrations"
    folder.mkdir(exist_ok=True)
    stem = f"{len(list(folder.glob('*.up.sql'))) + 1:03d}_rename_{table}_{old}"
    (folder / f"{stem}.up.sql").write_text(up, encoding="utf-8")
    (folder / f"{stem}.down.sql").write_text(down, encoding="utf-8")
    for database in databases(ws_dir, table, old):
        with closing(sqlite3.connect(database)) as conn:
            conn.executescript(up)
    return changed


def apply(ids: list[str], table: str, old: str, new: str) -> str:
    """Change every linked project; all of them keep the change only when all of their tests pass."""
    report: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cm6453_fed_", ignore_cleanup_errors=True) as tmp:
        _backup(ids, Path(tmp))
        try:
            schema = next((d for i in ids for d in databases(wb.safe_workspace_dir(i), table, old)), None)
            for ws_id in ids:
                ws_dir = wb.safe_workspace_dir(ws_id)
                changed = _rewrite(ws_dir, table, old, new)
                report.append(f"- `{ws_id}`: {', '.join(changed) or 'kodda geçmiyor'}")
            if schema is not None:
                types = typescript(schema)
                for ws_id in ids:
                    (wb.safe_workspace_dir(ws_id) / TYPES_FILE).write_text(types, encoding="utf-8")
            for ws_id in ids:
                ws_dir = wb.safe_workspace_dir(ws_id)
                if any(ws_dir.rglob("test_*.py")) and workspace_docker.available() and (failure := workspace_docker.run_tests(ws_dir, [])):
                    raise ValueError(f"{ws_id} testleri başarısız: {failure}")
        except (ValueError, OSError, sqlite3.Error) as exc:
            _restore(ids, Path(tmp))
            return f"Hiçbir proje değiştirilmedi (hepsi eski haline döndü): {exc}"
    for ws_id in ids:
        wb.create_snapshot(wb.safe_workspace_dir(ws_id), f"sözleşme: {table}.{old} -> {new}")
    return "Tüm bağlı projeler birlikte güncellendi:\n" + "\n".join(report) + f"\n- Göç dosyaları `migrations/`, tipler `{TYPES_FILE}`"


def preview(ids: list[str], table: str, old: str, new: str) -> str:
    lines = [f"**Etki alanı: `{table}.{old}` → `{new}`**"]
    for ws_id in ids:
        ws_dir = wb.safe_workspace_dir(ws_id)
        places = occurrences(ws_dir, old)
        lines.append(f"\n`{ws_id}`: {len(places)} yer")
        lines += [f"- {rel}:{number} `{text}`" for rel, number, text in places[:8]]
        if clash := occurrences(ws_dir, new):
            lines.append(f"- Uyarı: `{new}` zaten {len(clash)} yerde geçiyor")
        try:
            lines += [f"- Göç kanıtı: {round_trip(d, table, old, new)}" for d in databases(ws_dir, table, old)]
        except (ValueError, sqlite3.Error) as exc:
            lines.append(f"- Göç kanıtı BAŞARISIZ: {exc}")
    lines.append(f"\nHenüz hiçbir dosya değişmedi. Uygulamak için: `alan değiştir uygula: {table}.{old} -> {new}`")
    return "\n".join(lines)


def answer(prompt: str) -> str:
    if match := _LINK_RE.match(prompt):
        return link([n for n in re.split(r"\s*[,;]\s*", match["names"].strip()) if n])
    if not (match := _RENAME_RE.match(prompt)):
        return ""
    ids = linked()
    if not ids:
        return "Önce projeleri bağlayın: `sözleşme bağla: proje1, proje2`"
    run = apply if match["apply"] else preview
    return run(ids, match["table"], match["old"], match["new"])
