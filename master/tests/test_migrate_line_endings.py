"""A database migrated from a CRLF checkout opens from an LF checkout; real edits are still rejected."""

import hashlib

import pytest

import migrate

pytestmark = pytest.mark.unit


def test_line_endings_are_not_an_edit(tmp_path):
    sql = tmp_path / "0001_a.sql"
    sql.write_bytes(b"CREATE TABLE a (x);\n")
    db = tmp_path / "x.db"
    migrate.apply_pending(db, tmp_path)
    sql.write_bytes(b"CREATE TABLE a (x);\r\n")
    assert migrate.apply_pending(db, tmp_path) == []


def test_old_crlf_checksum_still_accepted_and_edit_rejected(tmp_path):
    sql = tmp_path / "0001_a.sql"
    sql.write_bytes(b"CREATE TABLE a (x);\n")
    migration = migrate.discover(tmp_path)[0]
    assert migrate._same_file(hashlib.sha256(b"CREATE TABLE a (x);\r\n").hexdigest(), migration)
    db = tmp_path / "x.db"
    migrate.apply_pending(db, tmp_path)
    sql.write_bytes(b"CREATE TABLE b (x);\n")
    with pytest.raises(migrate.MigrationError):
        migrate.apply_pending(db, tmp_path)
