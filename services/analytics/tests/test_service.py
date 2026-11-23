import pytest
import service as analytics


@pytest.mark.parametrize("raw, expected", [
    (None, "direct"),
    ("", "direct"),
    ("https://www.Google.com/search?q=x", "google.com"),
    ("https://t.co/abc", "t.co"),
])
def test_normalise_referrer(raw, expected):
    assert analytics.normalise_referrer(raw) == expected


def test_stats_count_clicks(db):
    analytics.record_click(db, "ie", "https://google.com")
    analytics.record_click(db, "ie", "https://www.google.com/x")
    analytics.record_click(db, "ie", None)
    analytics.record_click(db, "other", None)
    stats = analytics.get_stats(db, "ie")
    assert stats["total"] == 3
    assert stats["by_referrer"] == {"google.com": 2, "direct": 1}
    assert sum(stats["by_day"].values()) == 3


def test_stats_empty(db):
    assert analytics.get_stats(db, "none")["total"] == 0


def test_delete_clicks(db):
    analytics.record_click(db, "ie")
    analytics.delete_clicks(db, "ie")
    assert analytics.get_stats(db, "ie")["total"] == 0
