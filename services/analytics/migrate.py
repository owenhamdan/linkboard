"""Applies the numbered SQL files in migrations/ once each, in order, and records them."""
import logging
import os
import re

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
FILE_PATTERN = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
GO_LINE = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)

log = logging.getLogger("migrate")


def batches(sql):
    """Split a script on GO lines, like sqlcmd does."""
    return [b.strip() for b in GO_LINE.split(sql) if b.strip()]


def pending(conn, directory=MIGRATIONS_DIR):
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_migrations")
    applied = {row["version"] for row in cur.fetchall()}
    files = sorted(f for f in os.listdir(directory) if FILE_PATTERN.match(f))
    return [f for f in files if f[:3] not in applied]


def run(conn, directory=MIGRATIONS_DIR):
    cur = conn.cursor()
    cur.execute(
        "IF OBJECT_ID('schema_migrations') IS NULL "
        "CREATE TABLE schema_migrations ("
        "version NVARCHAR(10) NOT NULL PRIMARY KEY, "
        "name NVARCHAR(200) NOT NULL, "
        "applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME())"
    )
    conn.commit()
    todo = pending(conn, directory)
    for name in todo:
        with open(os.path.join(directory, name)) as f:
            sql = f.read()
        log.info("applying migration %s", name)
        try:
            for batch in batches(sql):
                cur.execute(batch)
            cur.execute("INSERT INTO schema_migrations (version, name) VALUES (%s, %s)", (name[:3], name))
            conn.commit()
        except Exception:
            conn.rollback()
            log.error("migration %s failed and was rolled back", name)
            raise
    if not todo:
        log.info("no pending migrations")
    return todo
