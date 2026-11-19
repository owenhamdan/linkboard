import migrate
from db import get_connection


def test_second_boot_applies_nothing(tmp_path):
    path = str(tmp_path / "test.db")
    get_connection(path).close()
    conn = get_connection(path)
    assert migrate.pending(conn) == []
    assert migrate.run(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] >= 1


def test_new_migration_keeps_existing_rows(tmp_path):
    conn = get_connection(":memory:")
    conn.execute("CREATE TABLE things (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO things (name) VALUES ('kept')")
    conn.commit()
    (tmp_path / "099_extra.sql").write_text("ALTER TABLE things ADD COLUMN note TEXT NOT NULL DEFAULT 'none';")
    assert migrate.run(conn, str(tmp_path)) == ["099_extra.sql"]
    assert tuple(conn.execute("SELECT name, note FROM things").fetchone()) == ("kept", "none")
    assert migrate.run(conn, str(tmp_path)) == []
