import os
import sqlite3

DB_PATH = os.environ.get("DATABASE_URL", "data/analytics.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    referrer TEXT,
    clicked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clicks_slug ON clicks(slug);
"""


def get_connection(path=None):
    path = path or DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def check(conn):
    """Return True if the database can be written to and read back."""
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS health_check (n INTEGER)")
        conn.execute("DELETE FROM health_check")
        conn.execute("INSERT INTO health_check (n) VALUES (1)")
        conn.commit()
        return conn.execute("SELECT n FROM health_check").fetchone()[0] == 1
    except Exception:
        return False
