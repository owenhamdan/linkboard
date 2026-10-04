import os
import sqlite3

DATA_DIR = os.environ.get("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "linkboard.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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
