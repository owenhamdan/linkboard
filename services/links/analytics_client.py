"""HTTP client for the analytics service. Every call has a timeout and never raises."""
import logging
import os

import requests

ANALYTICS_URL = os.environ.get("ANALYTICS_URL", "http://analytics:8000")
TIMEOUT_S = float(os.environ.get("ANALYTICS_TIMEOUT_S", "2"))

log = logging.getLogger(__name__)


def record_click(slug, referrer):
    try:
        r = requests.post(
            f"{ANALYTICS_URL}/clicks",
            json={"slug": slug, "referrer": referrer},
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("analytics unavailable, click for %s not recorded: %s", slug, e)
        return False


def delete_clicks(slug):
    try:
        r = requests.delete(f"{ANALYTICS_URL}/clicks/{slug}", timeout=TIMEOUT_S)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("analytics unavailable, clicks for %s not deleted: %s", slug, e)
        return False
