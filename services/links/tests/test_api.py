import pytest

import analytics_client
from app import create_app


@pytest.fixture
def client():
    return create_app(":memory:").test_client()


@pytest.fixture
def analytics_down(monkeypatch):
    monkeypatch.setattr(analytics_client, "ANALYTICS_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(analytics_client, "TIMEOUT_S", 0.5)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["db"] == "ok"


def test_create_get_list(client):
    assert client.post("/api/links", json={"url": "https://ie.edu", "slug": "iex"}).status_code == 201
    assert client.post("/api/links", json={"url": "nope"}).status_code == 400
    assert client.get("/api/links/iex").get_json()["url"] == "https://ie.edu"
    assert client.get("/api/links/zzz").status_code == 404
    assert len(client.get("/api/links").get_json()) == 1


def test_redirect_records_click(client, monkeypatch):
    calls = []
    monkeypatch.setattr(analytics_client, "record_click", lambda s, r: calls.append(s) or True)
    client.post("/api/links", json={"url": "https://ie.edu", "slug": "iex"})
    r = client.get("/iex")
    assert r.status_code == 302
    assert calls == ["iex"]
    assert client.get("/missing").status_code == 404


def test_redirect_works_when_analytics_down(client, analytics_down):
    client.post("/api/links", json={"url": "https://ie.edu", "slug": "iex"})
    r = client.get("/iex")
    assert r.status_code == 302
    assert r.headers["Location"] == "https://ie.edu"


def test_delete_when_analytics_down(client, analytics_down):
    client.post("/api/links", json={"url": "https://ie.edu", "slug": "iex"})
    r = client.delete("/api/links/iex")
    assert r.status_code == 200
    assert "warning" in r.get_json()
    assert client.delete("/api/links/iex").status_code == 404


def test_delete_when_analytics_up(client, monkeypatch):
    monkeypatch.setattr(analytics_client, "delete_clicks", lambda s: True)
    client.post("/api/links", json={"url": "https://ie.edu", "slug": "iex"})
    assert client.delete("/api/links/iex").status_code == 204
