"""SQL Server access: connection string parsing, connecting with retries, and a shared connection."""
import logging
import threading
import time
from contextlib import contextmanager
from urllib.parse import unquote, urlparse

import pymssql

log = logging.getLogger("db")


def parse_url(url):
    """Turn mssql://user:password@host:port/database into pymssql.connect arguments."""
    u = urlparse(url or "")
    if u.scheme != "mssql" or not u.hostname or not u.path.strip("/"):
        raise ValueError("DATABASE_URL must look like mssql://user:password@host:1433/database")
    return {
        "server": u.hostname,
        "port": u.port or 1433,
        "user": unquote(u.username or ""),
        "password": unquote(u.password or ""),
        "database": u.path.strip("/"),
    }


def connect(url, attempts=8, first_wait=2.0):
    """Connect, retrying with backoff. An Azure serverless database can take about a minute to resume."""
    params = parse_url(url)
    wait = first_wait
    for attempt in range(1, attempts + 1):
        try:
            return pymssql.connect(**params, login_timeout=15, timeout=30, as_dict=True, tds_version="7.4")
        except pymssql.OperationalError as e:
            if attempt == attempts:
                raise
            log.warning("database not ready (attempt %d/%d), retrying in %.0fs: %s", attempt, attempts, wait, e)
            time.sleep(wait)
            wait = min(wait * 2, 30)


class Database:
    """One connection per process, used by one request at a time and reopened if it breaks."""

    def __init__(self, url, attempts=8):
        self.url = url
        self.attempts = attempts
        self._conn = None
        self._lock = threading.Lock()

    @contextmanager
    def cursor(self):
        with self._lock:
            if self._conn is None:
                self._conn = connect(self.url, self.attempts)
            try:
                yield self._conn.cursor()
                self._conn.commit()
            except (pymssql.OperationalError, pymssql.InterfaceError):
                self._drop()
                raise
            except Exception:
                self._conn.rollback()
                raise

    def _drop(self):
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = None

    def close(self):
        with self._lock:
            if self._conn is not None:
                self._drop()


def check(db):
    """True if the service can write to and read from its own database."""
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE health_check SET checked_at = SYSUTCDATETIME() WHERE id = 1")
            cur.execute("SELECT checked_at FROM health_check WHERE id = 1")
            return cur.fetchone() is not None
    except Exception as e:
        log.warning("health check failed: %s", e)
        return False
