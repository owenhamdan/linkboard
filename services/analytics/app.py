import logging
import os
import time

from flask import Flask, g, jsonify, request

import service as analytics
from db import check, get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("analytics")
VERSION = os.environ.get("GIT_SHA", "dev")


def create_app(db_path=None):
    app = Flask(__name__)
    conn = get_connection(db_path)

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def log_request(response):
        ms = (time.perf_counter() - g.start) * 1000
        log.info("%s %s %s %.1fms", request.method, request.path, response.status_code, ms)
        return response

    @app.get("/health")
    def health():
        ok = check(conn)
        body = {"status": "ok" if ok else "error", "db": "ok" if ok else "error", "version": VERSION}
        return jsonify(body), 200 if ok else 503

    @app.post("/clicks")
    def api_record_click():
        data = request.get_json(silent=True) or {}
        slug = data.get("slug")
        if not slug:
            return jsonify(error="slug is required"), 400
        analytics.record_click(conn, slug, data.get("referrer"))
        return "", 201

    @app.delete("/clicks/<slug>")
    def api_delete_clicks(slug):
        analytics.delete_clicks(conn, slug)
        return "", 204

    @app.get("/stats/<slug>")
    def api_stats(slug):
        return jsonify(analytics.get_stats(conn, slug))

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
