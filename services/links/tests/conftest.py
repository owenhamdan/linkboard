"""Tests run against a real SQL Server (the compose stack locally, a service container in CI)."""
import os

import migrate
import pytest

from db import Database, connect

URL = os.environ.get("TEST_DATABASE_URL", "mssql://links_user:LocalDev_links_123@localhost:1433/links")


@pytest.fixture(scope="session")
def migrated():
    conn = connect(URL, attempts=10)
    migrate.run(conn)
    conn.close()


@pytest.fixture
def db(migrated):
    database = Database(URL)
    with database.cursor() as cur:
        cur.execute("DELETE FROM links")
    yield database
    database.close()
