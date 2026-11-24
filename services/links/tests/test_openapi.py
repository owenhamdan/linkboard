"""The committed openapi.yaml must describe exactly the routes the app serves."""
import os
import re

import yaml

from app import create_app
from tests.conftest import URL

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")


def documented():
    with open(SPEC_PATH) as f:
        spec = yaml.safe_load(f)
    return {(method.upper(), path) for path, ops in spec["paths"].items() for method in ops if method != "parameters"}


def implemented(app):
    routes = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule)
        routes |= {(method, path) for method in rule.methods - {"HEAD", "OPTIONS"}}
    return routes


def test_openapi_matches_routes(db):
    assert implemented(create_app(URL)) == documented()
