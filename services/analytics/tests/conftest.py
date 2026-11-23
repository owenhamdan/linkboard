"""Tests run against a real SQL Server (the compose stack locally, a service container in CI)."""
import os

import pytest

import migrate
from db import Database, connect

URL = os.environ.get("TEST_DATABASE_URL", "mssql://analytics_user:LocalDev_analytics_123@localhost:1433/analytics")


@pytest.fixture(scope="session")
def migrated():
    conn = connect(URL, attempts=10)
    migrate.run(conn)
    conn.close()


@pytest.fixture
def db(migrated):
    database = Database(URL)
    with database.cursor() as cur:
        cur.execute("DELETE FROM clicks")
    yield database
    database.close()
