import pytest

from analytics import service as analytics
from db import get_connection


@pytest.fixture
def conn():
    return get_connection(":memory:")


@pytest.mark.parametrize("raw, expected", [
    (None, "direct"),
    ("", "direct"),
    ("https://www.Google.com/search?q=x", "google.com"),
    ("https://t.co/abc", "t.co"),
])
def test_normalise_referrer(raw, expected):
    assert analytics.normalise_referrer(raw) == expected


def test_stats_count_clicks(conn):
    analytics.record_click(conn, "ie", "https://google.com")
    analytics.record_click(conn, "ie", "https://www.google.com/x")
    analytics.record_click(conn, "ie", None)
    analytics.record_click(conn, "other", None)
    stats = analytics.get_stats(conn, "ie")
    assert stats["total"] == 3
    assert stats["by_referrer"] == {"google.com": 2, "direct": 1}
    assert sum(stats["by_day"].values()) == 3


def test_stats_empty(conn):
    assert analytics.get_stats(conn, "none")["total"] == 0


def test_delete_clicks(conn):
    analytics.record_click(conn, "ie")
    analytics.delete_clicks(conn, "ie")
    assert analytics.get_stats(conn, "ie")["total"] == 0
