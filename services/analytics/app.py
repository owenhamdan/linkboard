import logging
import os
import time

import migrate
import pymssql
import service as analytics
from flask import Flask, g, jsonify, request

from db import Database, check, connect

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("analytics")
VERSION = os.environ.get("GIT_SHA", "dev")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:8080")


def create_app(database_url=None):
    url = database_url or os.environ.get("DATABASE_URL")
    conn = connect(url)
    try:
        migrate.run(conn)
    finally:
        conn.close()
    db = Database(url)
    app = Flask(__name__)

    @app.errorhandler(pymssql.Error)
    def database_unavailable(e):
        log.error("database error: %s", e)
        return jsonify(error="database unavailable, please try again shortly"), 503

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def log_request(response):
        ms = (time.perf_counter() - g.start) * 1000
        log.info("%s %s %s %.1fms", request.method, request.path, response.status_code, ms)
        origin = request.headers.get("Origin")
        if origin and origin in CORS_ORIGINS.split(","):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.get("/health")
    def health():
        ok = check(db)
        body = {"status": "ok" if ok else "error", "db": "ok" if ok else "error", "version": VERSION}
        return jsonify(body), 200 if ok else 503

    @app.post("/clicks")
    def api_record_click():
        data = request.get_json(silent=True) or {}
        slug = data.get("slug")
        if not slug:
            return jsonify(error="slug is required"), 400
        analytics.record_click(db, slug, data.get("referrer"))
        return "", 201

    @app.delete("/clicks/<slug>")
    def api_delete_clicks(slug):
        analytics.delete_clicks(db, slug)
        return "", 204

    @app.get("/stats/<slug>")
    def api_stats(slug):
        return jsonify(analytics.get_stats(db, slug))

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
