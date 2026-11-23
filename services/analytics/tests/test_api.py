import pytest

from app import create_app
from tests.conftest import URL


@pytest.fixture
def client(db):
    return create_app(URL).test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_record_stats_delete(client):
    assert client.post("/clicks", json={"slug": "iex", "referrer": "https://google.com"}).status_code == 201
    assert client.post("/clicks", json={}).status_code == 400
    assert client.get("/stats/iex").get_json()["total"] == 1
    assert client.delete("/clicks/iex").status_code == 204
    assert client.get("/stats/iex").get_json()["total"] == 0
