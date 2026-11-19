"""Applies numbered SQL files in migrations/ once each, in order, and records them."""
import logging
import os
import re

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
FILE_PATTERN = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")

log = logging.getLogger("migrate")


def pending(conn, directory=MIGRATIONS_DIR):
    applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
    files = sorted(f for f in os.listdir(directory) if FILE_PATTERN.match(f))
    return [f for f in files if f[:3] not in applied]


def run(conn, directory=MIGRATIONS_DIR):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, name TEXT NOT NULL, "
        "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    todo = pending(conn, directory)
    for name in todo:
        with open(os.path.join(directory, name)) as f:
            sql = f.read()
        log.info("applying migration %s", name)
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (name[:3], name))
        conn.commit()
    if not todo:
        log.info("no pending migrations")
    return todo
