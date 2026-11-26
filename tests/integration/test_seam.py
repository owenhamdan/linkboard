"""End to end tests across the seam, against the real compose stack.

Start it first with `docker compose up -d --build`. Stopping analytics is part
of the test, so it is started again at the end.
"""
import os
import subprocess
import time
import uuid

import pytest
import requests

LINKS = os.environ.get("LINKS_URL", "http://localhost:8001")
ANALYTICS = os.environ.get("ANALYTICS_URL", "http://localhost:8002")


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True, capture_output=True)


def wait_healthy(url, seconds=120):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/health", timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    pytest.fail(f"{url} never became healthy")


@pytest.fixture(scope="module", autouse=True)
def stack():
    wait_healthy(LINKS)
    wait_healthy(ANALYTICS)
    yield
    compose("start", "analytics")


def new_link():
    slug = "it_" + uuid.uuid4().hex[:8]
    r = requests.post(f"{LINKS}/api/links", json={"url": "https://www.ie.edu", "slug": slug}, timeout=5)
    assert r.status_code == 201
    return slug


def test_following_a_link_is_counted_by_analytics():
    slug = new_link()
    for _ in range(2):
        r = requests.get(f"{LINKS}/{slug}", allow_redirects=False, timeout=5)
        assert r.status_code == 302
        assert r.headers["Location"] == "https://www.ie.edu"
    stats = requests.get(f"{ANALYTICS}/stats/{slug}", timeout=5).json()
    assert stats["total"] == 2


def test_deleting_a_link_removes_its_clicks():
    slug = new_link()
    requests.get(f"{LINKS}/{slug}", allow_redirects=False, timeout=5)
    assert requests.delete(f"{LINKS}/api/links/{slug}", timeout=5).status_code == 204
    assert requests.get(f"{ANALYTICS}/stats/{slug}", timeout=5).json()["total"] == 0


def test_links_keeps_working_when_analytics_is_down():
    slug = new_link()
    compose("stop", "analytics")
    try:
        start = time.time()
        r = requests.get(f"{LINKS}/{slug}", allow_redirects=False, timeout=10)
        assert r.status_code == 302
        assert time.time() - start < 5, "the call to analytics must time out quickly"
        assert requests.get(f"{LINKS}/health", timeout=5).status_code == 200
        r = requests.delete(f"{LINKS}/api/links/{slug}", timeout=10)
        assert r.status_code == 200
        assert "warning" in r.json()
    finally:
        compose("start", "analytics")
        wait_healthy(ANALYTICS)
