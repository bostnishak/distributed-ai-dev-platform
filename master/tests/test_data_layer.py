"""DAT-01..03: shared connector, versioned migrations and single-file layout."""

import sqlite3
import threading

import pytest

import config
import db
import dbconn
import dbunify
import memory_engine
import migrate
import user_profile


def write(directory, name, sql):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(sql, encoding="utf-8")


def schema_of(path):
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
    finally:
        conn.close()
    return [r for r in rows if not r[1].startswith("search_index_")]


class TestConnector:
    def test_every_connection_gets_the_same_safety_settings(self, tmp_path):
        with dbconn.connection(tmp_path / "x.db") as conn:
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == dbconn.BUSY_TIMEOUT_MS
            assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
            assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"

    def test_connection_rolls_back_on_error_and_always_closes(self, tmp_path):
        with dbconn.connection(tmp_path / "x.db") as conn:
            conn.execute("CREATE TABLE t (v INTEGER)")
        with pytest.raises(RuntimeError), dbconn.connection(tmp_path / "x.db") as conn:
            conn.execute("INSERT INTO t VALUES (1)")
            raise RuntimeError("boom")
        with dbconn.connection(tmp_path / "x.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0

    def test_concurrent_writers_and_readers_never_hit_a_database_lock(self, tmp_path):
        path = tmp_path / "stress.db"
        with dbconn.connection(path) as conn:
            conn.execute("CREATE TABLE t (w INTEGER, n INTEGER)")
        errors: list[Exception] = []

        def writer(worker):
            try:
                for n in range(60):
                    with dbconn.connection(path) as conn:
                        conn.execute("INSERT INTO t VALUES (?, ?)", (worker, n))
            except Exception as exc:
                errors.append(exc)

        def reader():
            try:
                for _ in range(120):
                    with dbconn.connection(path) as conn:
                        conn.execute("SELECT COUNT(*) FROM t").fetchone()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
        threads += [threading.Thread(target=reader) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        assert errors == []
        with dbconn.connection(path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 8 * 60

    def test_database_file_follows_the_unified_switch(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        monkeypatch.setattr(config, "UNIFIED_DB", False)
        assert dbconn.database_file("user_profile.db") == tmp_path / "user_profile.db"
        monkeypatch.setattr(config, "UNIFIED_DB", True)
        assert dbconn.database_file("user_profile.db") == config.DB_PATH


class TestMigrations:
    def test_files_apply_in_order_once_and_are_recorded(self, tmp_path):
        mig = tmp_path / "m"
        write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER);")
        write(mig, "0002_b.sql", "CREATE TABLE b (id INTEGER); INSERT INTO a VALUES (1);")
        target = tmp_path / "t.db"
        assert migrate.apply_pending(target, mig) == ["0001_a.sql", "0002_b.sql"]
        assert migrate.apply_pending(target, mig) == []
        with dbconn.connection(target) as conn:
            assert [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2]
            assert conn.execute("SELECT COUNT(*) FROM a").fetchone()[0] == 1

    def test_failed_migration_rolls_back_completely_and_is_not_recorded(self, tmp_path):
        mig = tmp_path / "m"
        write(mig, "0001_ok.sql", "CREATE TABLE ok (id INTEGER);")
        write(mig, "0002_bad.sql", "CREATE TABLE half (id INTEGER); INSERT INTO missing VALUES (1);")
        target = tmp_path / "t.db"
        with pytest.raises(migrate.MigrationError, match=r"0002_bad.sql"):
            migrate.apply_pending(target, mig)
        with dbconn.connection(target) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "ok" in tables and "half" not in tables
            assert [r[0] for r in conn.execute("SELECT version FROM schema_migrations")] == [1]

    def test_editing_an_applied_migration_is_refused(self, tmp_path):
        mig = tmp_path / "m"
        write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER);")
        migrate.apply_pending(tmp_path / "t.db", mig)
        write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER, extra TEXT);")
        with pytest.raises(migrate.MigrationError, match="değiştirilmiş"):
            migrate.apply_pending(tmp_path / "t.db", mig)

    def test_bad_names_and_duplicate_versions_are_refused(self, tmp_path):
        write(tmp_path / "a", "init.sql", "SELECT 1;")
        with pytest.raises(migrate.MigrationError, match="NNNN"):
            migrate.discover(tmp_path / "a")
        write(tmp_path / "b", "0001_x.sql", "SELECT 1;")
        write(tmp_path / "b", "0001_y.sql", "SELECT 1;")
        with pytest.raises(migrate.MigrationError, match="yinelenen"):
            migrate.discover(tmp_path / "b")

    def test_out_of_order_file_is_refused(self, tmp_path):
        mig = tmp_path / "m"
        write(mig, "0002_b.sql", "CREATE TABLE b (id INTEGER);")
        migrate.apply_pending(tmp_path / "t.db", mig)
        write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER);")
        with pytest.raises(migrate.MigrationError, match="sıra bozuk"):
            migrate.apply_pending(tmp_path / "t.db", mig)

    def test_dry_run_changes_nothing_and_existing_data_is_snapshotted_first(self, tmp_path):
        mig = tmp_path / "m"
        write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER);")
        target = tmp_path / "t.db"
        with dbconn.connection(target) as conn:
            conn.execute("CREATE TABLE keep (v TEXT)")
            conn.execute("INSERT INTO keep VALUES ('x')")
        assert migrate.apply_pending(target, mig, dry_run=True) == ["0001_a.sql"]
        with dbconn.connection(target) as conn:
            assert "a" not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        migrate.apply_pending(target, mig, snapshot_dir=tmp_path / "snap")
        copies = list((tmp_path / "snap").glob("pre-migrate-t-*.db"))
        assert len(copies) == 1
        with dbconn.connection(copies[0]) as conn:
            assert conn.execute("SELECT v FROM keep").fetchone()[0] == "x"
            assert "a" not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}

    def test_only_the_newest_snapshots_are_kept(self, tmp_path):
        target = tmp_path / "t.db"
        with dbconn.connection(target) as conn:
            conn.execute("CREATE TABLE keep (v TEXT)")
        for _ in range(migrate.SNAPSHOTS_KEPT + 3):
            migrate.snapshot(target, tmp_path / "snap")
        assert len(list((tmp_path / "snap").glob("*.db"))) == migrate.SNAPSHOTS_KEPT

    def test_fresh_install_and_upgrade_from_the_legacy_schema_produce_the_same_schema(self, tmp_path, monkeypatch):
        fresh = tmp_path / "fresh" / "platform.db"
        monkeypatch.setattr(config, "DB_PATH", fresh)
        monkeypatch.setattr(config, "DATA_DIR", fresh.parent)
        db.init_db()

        legacy = tmp_path / "legacy" / "platform.db"
        monkeypatch.setattr(config, "DB_PATH", legacy)
        monkeypatch.setattr(config, "DATA_DIR", legacy.parent)
        monkeypatch.setattr(db, "MIGRATIONS_DIR", tmp_path / "no_sql_migrations")
        db.init_db()
        assert "files" not in {r[1] for r in schema_of(legacy)}
        monkeypatch.undo()
        monkeypatch.setattr(config, "DB_PATH", legacy)
        monkeypatch.setattr(config, "DATA_DIR", legacy.parent)
        db.init_db()
        assert schema_of(legacy) == schema_of(fresh)

    def test_real_migration_directory_applies_to_a_new_database(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        db.init_db()
        with db.connect() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        assert {"blobs", "files", "error_events", "feature_flags", "retention_policies", "search_index"} <= tables


def make_legacy(data_dir):
    with dbconn.connection(data_dir / "user_profile.db") as conn:
        conn.execute("CREATE TABLE profiles (user_id TEXT PRIMARY KEY, name TEXT)")
        conn.executemany("INSERT INTO profiles VALUES (?, ?)", [("a", "Ayşe"), ("b", "Berk")])
        conn.execute("CREATE INDEX idx_profiles_name ON profiles(name)")
    with dbconn.connection(data_dir / "cognitive_memory.db") as conn:
        conn.execute("CREATE TABLE conversations (id TEXT PRIMARY KEY, user_id TEXT, title TEXT)")
        conn.execute("INSERT INTO conversations VALUES ('c1', 'a', 'Merhaba')")
        conn.execute("CREATE VIRTUAL TABLE messages_fts USING fts5(body)")
        conn.execute("INSERT INTO messages_fts (body) VALUES ('sözleşme maddesi')")


class TestUnify:
    def test_rows_indexes_and_fts_content_move_to_the_platform_database(self, tmp_path):
        make_legacy(tmp_path)
        target = tmp_path / "platform.db"
        report = dbunify.unify(tmp_path, target)
        assert report["user_profile.db"] == {"profiles": 2}
        assert report["cognitive_memory.db"]["conversations"] == 1
        with dbconn.connection(target) as conn:
            assert conn.execute("SELECT name FROM profiles ORDER BY user_id").fetchall()[0][0] == "Ayşe"
            assert conn.execute("SELECT id FROM conversations").fetchone()[0] == "c1"
            assert conn.execute("SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'sözleşme'").fetchone()[0] == 1
            assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'idx_profiles_name'").fetchone()

    def test_legacy_files_are_renamed_not_deleted_and_a_second_run_does_nothing(self, tmp_path):
        make_legacy(tmp_path)
        dbunify.unify(tmp_path, tmp_path / "platform.db")
        assert not (tmp_path / "user_profile.db").exists()
        assert (tmp_path / "user_profile.db.migrated").is_file()
        assert dbunify.unify(tmp_path, tmp_path / "platform.db") == {}

    def test_existing_target_rows_are_not_overwritten(self, tmp_path):
        make_legacy(tmp_path)
        target = tmp_path / "platform.db"
        with dbconn.connection(target) as conn:
            conn.execute("CREATE TABLE profiles (user_id TEXT PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO profiles VALUES ('a', 'Yeni Ad')")
        dbunify.unify(tmp_path, target)
        with dbconn.connection(target) as conn:
            assert conn.execute("SELECT name FROM profiles WHERE user_id = 'a'").fetchone()[0] == "Yeni Ad"
            assert conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 2

    def test_modules_share_one_file_when_the_switch_is_on(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        monkeypatch.setattr(config, "UNIFIED_DB", True)
        make_legacy(tmp_path)
        db.init_db()
        user_profile.init_db()
        memory_engine.init_memory_db()
        assert sorted(p.name for p in tmp_path.glob("*.db")) == ["platform.db"]
        with db.connect() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"agents", "profiles", "conversations", "semantic_memories", "usage_events"} <= tables
        with db.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM profiles WHERE user_id IN ('a','b')").fetchone()[0] == 2
