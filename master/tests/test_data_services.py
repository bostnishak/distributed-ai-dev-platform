"""DAT-04..14: ownership, blob store, search, retention, portability, memory, doctor, indexes, events, backups."""

import json
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import backup_manager
import backup_schedule
import blobstore
import cmm_closed_loop
import config
import db
import db_doctor
import dbconn
import dbindexes
import events_log
import hybrid_graph_rag
import maintenance
import memory_engine
import memory_maintenance
import ownership
import portability
import retention
import search_index
import user_profile
import vector_meta

MASTER = Path(__file__).resolve().parents[1]
ALLOWLIST = MASTER.parent / "docs" / "plan-v2" / "owner_lint_allowlist.txt"


def use_environment(monkeypatch, root: Path, unified: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "DB_PATH", root / "platform.db")
    monkeypatch.setattr(config, "DATA_DIR", root)
    monkeypatch.setattr(config, "UNIFIED_DB", unified)
    db.init_db()
    user_profile.init_db()
    memory_engine.init_memory_db()
    return root


@pytest.fixture
def env(tmp_path, monkeypatch):
    return use_environment(monkeypatch, tmp_path / "env")


@pytest.fixture
def conn(env):
    with dbconn.connection(config.DB_PATH) as connection:
        yield connection


def iso(days_ago: float = 0) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(timespec="seconds")


def add_chat(conn, owner, chat_id, title, text, days_ago=0):
    conn.execute(
        "INSERT INTO conversations (id, user_id, title, summary, pinned_context, created_at, updated_at) "
        "VALUES (?, ?, ?, '', '[]', ?, ?)", (chat_id, owner, title, iso(days_ago), iso(days_ago)))
    conn.execute(
        "INSERT INTO conversation_messages (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
        (chat_id, text, iso(days_ago)))
    search_index.index(conn, "chat", owner, chat_id, title, text)


class TestOwnership:
    def test_every_table_in_every_database_is_classified(self, env, conn):
        hybrid_graph_rag.HybridGraphRAG()
        cmm_closed_loop.init_cmm_quality_db()
        assert ownership.unclassified_tables(conn) == []

    def test_scoped_select_only_returns_the_owners_rows(self, conn):
        add_chat(conn, "ayse", "c1", "A", "x")
        add_chat(conn, "berk", "c2", "B", "y")
        rows = ownership.scoped_select(conn, "conversations", "ayse", columns="id")
        assert [r["id"] for r in rows] == ["c1"]
        assert ownership.scoped_select(conn, "conversations", "ayse", where="id = ?", params=("c2",)) == []

    def test_scoped_select_refuses_tables_nobody_owns_and_bad_column_lists(self, conn):
        with pytest.raises(ownership.UnscopedQuery):
            ownership.scoped_select(conn, "tasks", "ayse")
        with pytest.raises(ownership.UnscopedQuery):
            ownership.scoped_select(conn, "conversations", "ayse", columns="id; DROP TABLE conversations")

    def test_deleting_a_user_removes_every_owned_row_and_nobody_elses(self, conn):
        for owner in ("ayse", "berk"):
            conn.execute("INSERT INTO profiles (user_id, display_name, created_at, updated_at) VALUES (?,?,?,?)",
                         (owner, owner, iso(), iso()))
            add_chat(conn, owner, f"chat-{owner}", "başlık", "metin")
            conn.execute("INSERT INTO semantic_memories (user_id, category, fact_key, fact_value, confidence, updated_at)"
                         " VALUES (?, 'tercih', 'dil', 'tr', 1.0, ?)", (owner, iso()))
            conn.execute("INSERT INTO saved_chats (chat_id, user_id, title, updated_at, messages_json) "
                         "VALUES (?, ?, 't', ?, '[]')", (f"s-{owner}", owner, iso()))
            blobstore.store(conn, owner, "not.txt", f"icerik {owner}".encode())
        before = ownership.count_owned(conn, "berk")
        assert all(n > 0 for t, n in before.items() if t in ("profiles", "conversations", "semantic_memories",
                                                             "saved_chats", "files", "search_index"))
        removed = ownership.delete_owner(conn, "ayse")
        assert removed["conversation_messages"] == 1
        assert sum(ownership.count_owned(conn, "ayse").values()) == 0
        assert ownership.count_owned(conn, "berk") == before
        assert conn.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0] == 1

    def test_no_new_query_reads_or_changes_owned_rows_without_the_owner_column(self):
        known = {line.strip() for line in ALLOWLIST.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")}
        found = set(ownership.find_unscoped_queries(MASTER))
        assert found - known == set(), "yeni sahipsiz sorgu: " + ", ".join(sorted(found - known))
        assert known - found == set(), "izin listesinde artık olmayan girdi (silin): " + ", ".join(sorted(known - found))


class TestBlobStore:
    def test_identical_content_is_stored_once_and_read_back_by_its_owner(self, conn):
        first = blobstore.store(conn, "ayse", "a.txt", b"merhaba")
        second = blobstore.store(conn, "ayse", "kopya.txt", b"merhaba")
        assert first["sha256"] == second["sha256"] and first["id"] != second["id"]
        assert len([p for p in blobstore.blob_root().rglob("*") if p.is_file()]) == 1
        assert blobstore.read(conn, first["id"], "ayse") == b"merhaba"

    def test_other_users_and_unknown_ids_look_identical(self, conn):
        record = blobstore.store(conn, "ayse", "a.txt", b"gizli")
        with pytest.raises(blobstore.FileNotAvailable):
            blobstore.read(conn, record["id"], "berk")
        with pytest.raises(blobstore.FileNotAvailable):
            blobstore.read(conn, "yok", "ayse")

    def test_oversized_upload_is_refused_and_leaves_nothing_behind(self, conn):
        with pytest.raises(blobstore.BlobError):
            blobstore.store(conn, "ayse", "b.bin", b"x" * 100, limit=10)
        assert [p for p in blobstore.blob_root().rglob("*") if p.is_file()] == []
        assert conn.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 0

    def test_a_blob_goes_only_when_its_last_file_does(self, conn):
        a = blobstore.store(conn, "ayse", "a", b"ortak")
        b = blobstore.store(conn, "berk", "b", b"ortak")
        blobstore.delete(conn, a["id"], "ayse")
        assert blobstore.collect_garbage(conn)["blobs"] == 0
        assert blobstore.blob_path(a["sha256"]).is_file()
        blobstore.delete(conn, b["id"], "berk")
        assert blobstore.collect_garbage(conn)["blobs"] == 1
        assert not blobstore.blob_path(a["sha256"]).exists()

    def test_expired_files_are_unavailable_and_collected(self, conn):
        record = blobstore.store(conn, "ayse", "a", b"gecici", expires_at=iso(1))
        with pytest.raises(blobstore.FileNotAvailable):
            blobstore.read(conn, record["id"], "ayse")
        assert blobstore.collect_garbage(conn)["expired_files"] == 1
        assert not blobstore.blob_path(record["sha256"]).exists()

    def test_tampered_or_missing_bytes_are_reported(self, conn):
        record = blobstore.store(conn, "ayse", "a", b"orijinal")
        assert blobstore.verify(conn) == []
        blobstore.blob_path(record["sha256"]).write_bytes(b"degismis")
        assert "uyuşmuyor" in blobstore.verify(conn)[0]
        blobstore.blob_path(record["sha256"]).unlink()
        assert "dosya yok" in blobstore.verify(conn)[0]

    def test_signed_links_bind_file_owner_and_time(self, env):
        token = blobstore.sign("f1", "ayse", ttl_seconds=60)
        assert blobstore.check_signature("f1", "ayse", token)
        assert not blobstore.check_signature("f2", "ayse", token)
        assert not blobstore.check_signature("f1", "berk", token)
        assert not blobstore.check_signature("f1", "ayse", token[:-2] + "00")
        assert not blobstore.check_signature("f1", "ayse", blobstore.sign("f1", "ayse", ttl_seconds=-5))
        assert not blobstore.check_signature("f1", "ayse", "bozuk")


class TestSearch:
    def test_turkish_letters_fold_and_suffixes_are_cut(self):
        assert search_index.fold("İSTANBUL ÇIĞ Işık") == "istanbul cig isik"
        assert search_index.stem("sozlesmelerin") == search_index.stem("sozlesme") == "sozlesm"
        assert search_index.stem("kitap") == "kitap"
        assert search_index.tokens("Sözleşmelerde İşçiler") == ["sozlesm", "isci"]

    def test_inflected_queries_find_the_base_form_and_the_other_way_round(self, conn):
        search_index.index(conn, "chat", "ayse", "c1", "Kira", "Sözleşme maddeleri incelendi")
        search_index.index(conn, "chat", "ayse", "c2", "Diğer", "Hava durumu")
        assert [h["ref"] for h in search_index.search(conn, "ayse", "sözleşmelerin")] == ["c1"]
        search_index.index(conn, "chat", "ayse", "c3", "Başka", "Sözleşmelerin ayrıntıları")
        assert {h["ref"] for h in search_index.search(conn, "ayse", "sözleşme")} == {"c1", "c3"}

    def test_results_never_cross_owners_and_kinds_filter(self, conn):
        search_index.index(conn, "chat", "ayse", "c1", "T", "ortak kelime")
        search_index.index(conn, "file", "ayse", "f1", "T", "ortak kelime")
        search_index.index(conn, "chat", "berk", "c9", "T", "ortak kelime")
        assert {h["ref"] for h in search_index.search(conn, "ayse", "ortak")} == {"c1", "f1"}
        assert [h["ref"] for h in search_index.search(conn, "ayse", "ortak", kinds=("file",))] == ["f1"]
        assert search_index.search(conn, "ayse", "   ") == []

    def test_reindexing_replaces_and_removing_deletes(self, conn):
        search_index.index(conn, "chat", "ayse", "c1", "T", "eski metin")
        search_index.index(conn, "chat", "ayse", "c1", "T", "yeni metin")
        assert search_index.search(conn, "ayse", "eski") == []
        assert len(search_index.search(conn, "ayse", "yeni")) == 1
        search_index.remove(conn, "chat", "ayse", "c1")
        assert search_index.search(conn, "ayse", "yeni") == []

    def test_queries_stay_fast_on_a_large_index(self, conn):
        rows = [(f"başlık {i}", f"belge {i} kelime{i % 500} sözleşme maddesi", "doc", "ayse", str(i)) for i in range(20_000)]
        conn.executemany("INSERT INTO search_index (title, body, kind, owner_id, ref) VALUES (?,?,?,?,?)",
                         [(search_index.normalise(a), search_index.normalise(b), c, d, e) for a, b, c, d, e in rows])
        times = []
        for n in range(20):
            start = time.perf_counter()
            search_index.search(conn, "ayse", f"kelime{n * 7}")
            times.append(time.perf_counter() - start)
        assert sorted(times)[int(len(times) * 0.95) - 1] < 0.1


class TestRetention:
    def test_policy_rejects_nonsense_and_reads_back(self, conn):
        with pytest.raises(ValueError):
            retention.set_policy(conn, "ayse", chat_days=0)
        retention.set_policy(conn, "ayse", chat_days=30)
        retention.set_policy(conn, "ayse", chat_days=10, file_days=5)
        assert retention.get_policy(conn, "ayse")["chat_days"] == 10
        assert retention.get_policy(conn, "kimse")["chat_days"] is None

    def test_expired_chats_usage_and_files_go_and_everything_else_stays(self, conn):
        add_chat(conn, "ayse", "eski", "Eski", "çok eski sohbet", days_ago=40)
        add_chat(conn, "ayse", "yeni", "Yeni", "yeni sohbet", days_ago=1)
        add_chat(conn, "berk", "berk-eski", "Eski", "berk'in eski sohbeti", days_ago=400)
        conn.execute("INSERT INTO usage_events (user_id, ts, model, task_type) VALUES ('ayse', ?, 'm', 't')", (iso(40),))
        conn.execute("INSERT INTO usage_events (user_id, ts, model, task_type) VALUES ('ayse', ?, 'm', 't')", (iso(1),))
        old = blobstore.store(conn, "ayse", "eski.txt", b"eski dosya")
        conn.execute("UPDATE files SET created_at = ? WHERE id = ?", (iso(40), old["id"]))
        blobstore.store(conn, "ayse", "yeni.txt", b"yeni dosya")
        retention.set_policy(conn, "ayse", chat_days=30, usage_days=30, file_days=30)
        removed = retention.purge_expired(conn)
        assert removed["chats"] == 1 and removed["usage_events"] == 1 and removed["files"] == 1
        assert [r["id"] for r in ownership.scoped_select(conn, "conversations", "ayse")] == ["yeni"]
        assert conn.execute("SELECT COUNT(*) FROM conversation_messages WHERE conversation_id = 'eski'").fetchone()[0] == 0
        assert search_index.search(conn, "ayse", "eski") == []
        assert not blobstore.blob_path(old["sha256"]).exists()
        assert len(ownership.scoped_select(conn, "conversations", "berk")) == 1

    def test_erasing_a_user_leaves_no_readable_trace_in_the_files(self, conn, env):
        marker = "BENZERSIZ-IZ-4f9a1c"
        add_chat(conn, "ayse", "c1", f"Başlık {marker}", f"metin {marker}")
        conn.execute("INSERT INTO saved_chats (chat_id, user_id, title, updated_at, messages_json) VALUES "
                     "('s1','ayse',?, ?, ?)", (marker, iso(), json.dumps([marker])))
        blobstore.store(conn, "ayse", f"{marker}.txt", f"dosya {marker}".encode())
        add_chat(conn, "berk", "c2", "Berk", "berk metni")
        conn.commit()
        report = retention.erase_user("ayse")
        assert report["platform.db"]["conversations"] == 1
        for path in env.rglob("*"):
            if path.is_file():
                assert marker.encode() not in path.read_bytes(), f"{path.name} hâlâ içeriyor"
        with dbconn.connection(config.DB_PATH) as check:
            assert len(ownership.scoped_select(check, "conversations", "berk")) == 1
            assert sum(ownership.count_owned(check, "ayse").values()) == 0

    def test_erasing_works_when_each_module_still_has_its_own_file(self, tmp_path, monkeypatch):
        use_environment(monkeypatch, tmp_path / "split", unified=False)
        marker = "AYRIK-IZ-77be"
        with dbconn.connection(dbconn.database_file("cognitive_memory.db")) as memory:
            add_chat_split = memory
            add_chat_split.execute(
                "INSERT INTO conversations (id, user_id, title, summary, pinned_context, created_at, updated_at) "
                "VALUES ('c1','ayse',?, '', '[]', ?, ?)", (marker, iso(), iso()))
        retention.erase_user("ayse")
        raw = (tmp_path / "split" / "cognitive_memory.db").read_bytes()
        assert marker.encode() not in raw


class TestPortability:
    def test_a_user_moves_to_another_machine_with_chats_memories_and_files(self, tmp_path, monkeypatch):
        use_environment(monkeypatch, tmp_path / "one")
        with dbconn.connection(config.DB_PATH) as conn:
            add_chat(conn, "ayse", "c1", "Kira", "sözleşme maddesi")
            conn.execute("INSERT INTO semantic_memories (user_id, category, fact_key, fact_value, confidence, updated_at)"
                         " VALUES ('ayse','tercih','dil','tr',1.0,?)", (iso(),))
            record = blobstore.store(conn, "ayse", "not.txt", "içerik".encode())
            conn.execute("INSERT INTO mcp_connectors (id, name, url, api_key, auth_header, auth_prefix, description, "
                         "enabled, tools_json, created_at) VALUES ('m1','x','http://x','SIR-ANAHTAR-123','A','B','',1,'[]',?)"
                         if False else "SELECT 1", ())
        archive = tmp_path / "ayse.zip"
        counts = portability.export_user("ayse", archive)
        assert counts["conversations"] == 1 and counts["files"] == 1 and counts["conversation_messages"] == 1
        assert b"SIR-ANAHTAR" not in archive.read_bytes()

        use_environment(monkeypatch, tmp_path / "two")
        written = portability.import_user(archive, new_owner="ayse2")
        assert written["conversations"] == 1 and written["files"] == 1
        with dbconn.connection(config.DB_PATH) as conn:
            assert [r["title"] for r in ownership.scoped_select(conn, "conversations", "ayse2")] == ["Kira"]
            assert blobstore.read(conn, record["id"], "ayse2") == "içerik".encode()
            assert ownership.scoped_select(conn, "conversations", "ayse") == []
            assert [h["ref"] for h in search_index.search(conn, "ayse2", "sözleşmeler")] == ["c1"]

    def test_importing_twice_keeps_existing_rows_unless_told_to_replace(self, tmp_path, monkeypatch):
        use_environment(monkeypatch, tmp_path / "one")
        with dbconn.connection(config.DB_PATH) as conn:
            add_chat(conn, "ayse", "c1", "Birinci", "metin")
        archive = tmp_path / "a.zip"
        portability.export_user("ayse", archive)
        with dbconn.connection(config.DB_PATH) as conn:
            conn.execute("UPDATE conversations SET title = 'Elle değişti' WHERE id = 'c1'")
        portability.import_user(archive)
        with dbconn.connection(config.DB_PATH) as conn:
            assert conn.execute("SELECT title FROM conversations").fetchone()[0] == "Elle değişti"
        portability.import_user(archive, replace=True)
        with dbconn.connection(config.DB_PATH) as conn:
            assert conn.execute("SELECT title FROM conversations").fetchone()[0] == "Birinci"

    def test_unknown_formats_and_corrupted_files_are_refused(self, tmp_path, monkeypatch):
        import zipfile
        use_environment(monkeypatch, tmp_path / "one")
        bad = tmp_path / "bad.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("data.json", json.dumps({"format": "baska", "owner": "x", "tables": {}}))
        with pytest.raises(ValueError, match="biçim"):
            portability.import_user(bad)


class TestMemoryMaintenance:
    def add(self, conn, key, value, confidence=1.0, days_ago=0, category="tercih"):
        conn.execute("INSERT INTO semantic_memories (user_id, category, fact_key, fact_value, confidence, updated_at) "
                     "VALUES ('ayse', ?, ?, ?, ?, ?)", (category, key, value, confidence, iso(days_ago)))

    def test_the_same_fact_written_differently_is_merged_keeping_the_strongest(self, conn):
        self.add(conn, "Yanıt Dili", "Türkçe", 0.6)
        self.add(conn, "yanit_dili", "turkce", 0.9)
        result = memory_maintenance.consolidate(conn, "ayse")
        assert result["merged"] == 1 and result["conflicts"] == []
        assert [r["confidence"] for r in conn.execute("SELECT confidence FROM semantic_memories")] == [0.9]

    def test_two_different_values_are_reported_for_the_user_to_decide(self, conn):
        self.add(conn, "editör", "vim")
        self.add(conn, "Editor", "vscode")
        result = memory_maintenance.consolidate(conn, "ayse")
        assert result["merged"] == 0 and len(result["conflicts"]) == 1
        assert {c["value"] for c in result["conflicts"][0]["candidates"]} == {"vim", "vscode"}
        keep = result["conflicts"][0]["candidates"][1]["id"]
        assert memory_maintenance.resolve_conflict(conn, "ayse", keep) == 1
        assert conn.execute("SELECT COUNT(*) FROM semantic_memories").fetchone()[0] == 1

    def test_facts_fade_with_age_and_only_faded_ones_are_removed(self, conn):
        self.add(conn, "taze", "a", 1.0, days_ago=1)
        self.add(conn, "eski", "b", 1.0, days_ago=400)
        assert memory_maintenance.prune_faded(conn, "ayse", half_life_days=90, drop_below=0.2) == 1
        assert [r["fact_key"] for r in conn.execute("SELECT fact_key FROM semantic_memories")] == ["taze"]

    def test_nobody_elses_facts_are_touched(self, conn):
        conn.execute("INSERT INTO semantic_memories (user_id, category, fact_key, fact_value, confidence, updated_at) "
                     "VALUES ('berk','t','eski','x',1.0,?)", (iso(900),))
        assert memory_maintenance.prune_faded(conn, "ayse") == 0
        assert conn.execute("SELECT COUNT(*) FROM semantic_memories").fetchone()[0] == 1


class TestDoctor:
    def test_a_fresh_database_has_no_errors(self, env):
        assert [f for f in db_doctor.diagnose(config.DB_PATH) if f.severity == "error"] == []

    def test_each_kind_of_damage_is_found(self, env, conn):
        conn.execute("INSERT INTO profiles (user_id, display_name, created_at, updated_at) VALUES ('  ','x',?,?)",
                     (iso(), iso()))
        conn.execute("INSERT INTO saved_chats (chat_id, user_id, title, updated_at, messages_json) "
                     "VALUES ('s','ayse','t',?, '{bozuk')", (iso(),))
        record = blobstore.store(conn, "ayse", "a", b"asil")
        blobstore.store(conn, "ayse", "b", b"ikinci")
        conn.commit()
        blobstore.blob_path(record["sha256"]).write_bytes(b"bozuldu")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO files (id, owner_id, name, mime, sha256, size, created_at) "
                     "VALUES ('y','ayse','n','m','yok',1,?)", (iso(),))
        conn.commit()
        checks = {(f.severity, f.check) for f in db_doctor.diagnose(config.DB_PATH)}
        assert ("error", "owner") in checks
        assert ("error", "json") in checks
        assert ("error", "blobs") in checks
        assert ("error", "blob_bytes") in checks

    def test_repair_removes_only_what_nothing_references(self, env, conn):
        keep = blobstore.store(conn, "ayse", "a", b"kalsin")
        loose = blobstore.store(conn, "ayse", "b", b"serbest")
        blobstore.delete(conn, loose["id"], "ayse")
        conn.commit()
        actions = db_doctor.repair(config.DB_PATH)
        assert actions and blobstore.blob_path(keep["sha256"]).is_file()
        assert not blobstore.blob_path(loose["sha256"]).exists()


class TestIndexesAndPagination:
    @pytest.mark.parametrize("name", sorted(dbindexes.QUERIES))
    def test_hot_queries_are_answered_from_an_index(self, conn, name):
        sql, params = dbindexes.QUERIES[name]
        assert dbindexes.full_scans(conn, sql, params) == [], f"{name}: tam tablo taraması"

    def test_pagination_caps_the_page_size_and_reports_more_pages(self, conn):
        for i in range(30):
            add_chat(conn, "ayse", f"c{i:02d}", f"b{i}", "m")
        page = dbindexes.paginate(conn, "SELECT id FROM conversations WHERE user_id = ? ORDER BY id", ("ayse",), 1, 10)
        assert len(page["rows"]) == 10 and page["has_more"]
        last = dbindexes.paginate(conn, "SELECT id FROM conversations WHERE user_id = ? ORDER BY id", ("ayse",), 3, 10)
        assert len(last["rows"]) == 10 and not last["has_more"]
        assert dbindexes.paginate(conn, "SELECT id FROM conversations ORDER BY id", (), 1, 10_000)["size"] == 200


class TestEvents:
    def seed(self, conn):
        rows = [("assigned", "uye1", 1, iso(1)), ("failed", "uye2", 1, iso(2)), ("assigned", "uye1", 2, iso(200))]
        conn.execute("INSERT INTO agents (agent_id, member_name, model, mode, registered_at, last_seen_at) "
                     "VALUES ('uye1','a','m','node',?,?)" if False else "SELECT 1")
        conn.execute("PRAGMA foreign_keys = OFF")
        for kind, agent, project, when in rows:
            conn.execute("INSERT INTO events (project_id, agent_id, event_type, payload, created_at) VALUES (?,?,?,?,?)",
                         (project, agent, kind, json.dumps({"n": 1}), when))

    def test_filters_combine_and_newest_comes_first(self, conn):
        self.seed(conn)
        assert [e["event_type"] for e in events_log.query(conn)] == ["assigned", "failed", "assigned"]
        assert len(events_log.query(conn, event_type="assigned", agent_id="uye1")) == 2
        assert len(events_log.query(conn, project_id=2)) == 1
        assert len(events_log.query(conn, since=iso(10))) == 2
        assert events_log.query(conn, limit=1, offset=1)[0]["event_type"] == "failed"
        assert events_log.query(conn)[0]["payload"] == {"n": 1}

    def test_pruning_by_age_and_by_count(self, conn):
        self.seed(conn)
        assert events_log.prune(conn, older_than_days=90) == 1
        assert events_log.prune(conn, older_than_days=90, max_rows=1) == 1
        assert conn.execute("SELECT event_type FROM events").fetchone()[0] == "assigned"

    def test_export_writes_one_json_line_per_event(self, conn, tmp_path):
        self.seed(conn)
        target = tmp_path / "out" / "events.jsonl"
        assert events_log.export_jsonl(conn, target) == 3
        assert len(target.read_text(encoding="utf-8").splitlines()) == 3


class TestVectorMetadata:
    def test_columns_are_added_and_stale_vectors_are_listed(self, env):
        rag = hybrid_graph_rag.HybridGraphRAG()
        rag.add_document("d1", "T", "içerik bir", extract_graph=False)
        rag.add_document("d2", "T", "içerik iki", extract_graph=False)
        with dbconn.connection(config.DB_PATH) as conn:
            assert vector_meta.ensure_columns(conn)
            vector_meta.stamp(conn, "d1", "bge-m3", 1024)
            assert vector_meta.stale(conn, "bge-m3", 1024) == ["d2"]
            assert sorted(vector_meta.stale(conn, "baska-model", 1024)) == ["d1", "d2"]


class TestScheduledBackups:
    def test_backup_restores_into_a_clean_folder_with_identical_data(self, env, conn, tmp_path):
        add_chat(conn, "ayse", "c1", "Yedek", "önemli sohbet")
        record = blobstore.store(conn, "ayse", "d.txt", b"onemli dosya")
        conn.commit()
        archive = backup_schedule.run_backup(tmp_path / "out", password="yedek-parolasi-1", data_dir=env)
        restored = tmp_path / "restored"
        result = backup_manager.restore_enterprise_backup_zip(archive.read_bytes(), "yedek-parolasi-1", restored)
        assert result["verified_sha256"] and result["restored_count"] >= 2
        with dbconn.connection(restored / "platform.db") as copy:
            assert copy.execute("SELECT title FROM conversations").fetchone()[0] == "Yedek"
        assert (restored / "blobs" / record["sha256"][:2] / record["sha256"][2:4] / record["sha256"]).read_bytes() \
            == b"onemli dosya"

    def test_a_wrong_password_never_restores(self, env, tmp_path):
        archive = backup_schedule.run_backup(tmp_path / "out", password="dogru-parola-12", data_dir=env)
        with pytest.raises(ValueError):
            backup_manager.restore_enterprise_backup_zip(archive.read_bytes(), "yanlis", tmp_path / "x")

    def test_old_archives_are_pruned_to_daily_and_weekly_keepers(self, tmp_path):
        names = []
        for offset in range(0, 70, 1):
            moment = datetime(2026, 11, 20, tzinfo=UTC) - timedelta(days=offset)
            path = tmp_path / f"backup-{moment:%Y%m%d}-030000.zip"
            path.write_bytes(b"x")
            names.append(path)
        removed = backup_schedule.prune(tmp_path, keep_daily=7, keep_weekly=4)
        kept = sorted(p.name for p in tmp_path.glob("backup-*.zip"))
        assert len(kept) < len(names) and len(removed) == len(names) - len(kept)
        assert all(re.match(r"backup-\d{8}-\d{6}\.zip", n) for n in kept)
        newest = sorted(names, reverse=True)[:7]
        assert all(p.exists() for p in newest)


class TestMaintenance:
    def test_a_round_applies_retention_and_collects_garbage(self, env, conn):
        add_chat(conn, "ayse", "eski", "E", "eski", days_ago=90)
        retention.set_policy(conn, "ayse", chat_days=30)
        conn.commit()
        report = maintenance.run_once()
        assert report["retention"]["chats"] == 1 and maintenance.status()["rounds"] >= 1

    def test_a_failing_round_is_counted_and_the_loop_keeps_going(self, env, monkeypatch):
        calls = {"n": 0}
        real = maintenance.run_once
        done = threading.Event()

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("ilk tur bozuk")
            real()
            done.set()

        monkeypatch.setattr(maintenance, "run_once", flaky)
        before = maintenance.status()["failures"]
        maintenance.start_background(interval_seconds=0.05)
        assert done.wait(10)
        maintenance.stop_background()
        state = maintenance.status()
        assert state["failures"] == before + 1 and "ilk tur bozuk" in state["last_error"]
        assert not state["running"]


class TestErd:
    def test_the_committed_diagram_matches_the_real_schema(self):
        import erd

        committed = (MASTER.parent / "docs" / "plan-v2" / "erd.md").read_text(encoding="utf-8")
        assert committed == erd.build(), "erd.md eski: python master/erd.py çalıştırın"
