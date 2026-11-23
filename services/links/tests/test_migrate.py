import migrate
import pytest

from db import connect, parse_url
from tests.conftest import URL


@pytest.fixture
def conn(migrated):
    c = connect(URL)
    cur = c.cursor()
    cur.execute("IF OBJECT_ID('mig_test') IS NOT NULL DROP TABLE mig_test")
    cur.execute("DELETE FROM schema_migrations WHERE version IN ('098', '099')")
    c.commit()
    yield c
    cur.execute("IF OBJECT_ID('mig_test') IS NOT NULL DROP TABLE mig_test")
    cur.execute("DELETE FROM schema_migrations WHERE version IN ('098', '099')")
    c.commit()
    c.close()


def test_second_boot_applies_nothing(conn):
    assert migrate.pending(conn) == []
    assert migrate.run(conn) == []


def test_new_migration_keeps_existing_rows(conn, tmp_path):
    cur = conn.cursor()
    cur.execute("CREATE TABLE mig_test (id INT PRIMARY KEY, name NVARCHAR(20))")
    cur.execute("INSERT INTO mig_test (id, name) VALUES (1, 'kept')")
    conn.commit()
    (tmp_path / "099_add_note.sql").write_text(
        "ALTER TABLE mig_test ADD note NVARCHAR(20) NOT NULL CONSTRAINT df_mig_test_note DEFAULT 'none';"
    )
    assert migrate.run(conn, str(tmp_path)) == ["099_add_note.sql"]
    cur.execute("SELECT name, note FROM mig_test")
    assert cur.fetchone() == {"name": "kept", "note": "none"}
    assert migrate.run(conn, str(tmp_path)) == []


def test_failed_migration_is_rolled_back(conn, tmp_path):
    (tmp_path / "098_broken.sql").write_text("CREATE TABLE mig_test (id INT);\nGO\nSELECT * FROM no_such_table;")
    with pytest.raises(Exception):
        migrate.run(conn, str(tmp_path))
    cur = conn.cursor()
    cur.execute("SELECT OBJECT_ID('mig_test') AS id")
    assert cur.fetchone()["id"] is None
    assert migrate.pending(conn, str(tmp_path)) == ["098_broken.sql"]


def test_batches_split_on_go():
    assert migrate.batches("A;\nGO\nB;\n go \n\n") == ["A;", "B;"]


def test_parse_url():
    p = parse_url("mssql://u%40x:p%21w@host.example:1444/mydb")
    assert p == {"server": "host.example", "port": 1444, "user": "u@x", "password": "p!w", "database": "mydb"}
    with pytest.raises(ValueError):
        parse_url("sqlite:///x.db")
