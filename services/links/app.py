import logging
import os
import time

import pymssql
from flask import Flask, abort, g, jsonify, redirect, request

import analytics_client
import migrate
import service as links
from db import Database, check, connect

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("links")
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

    @app.post("/api/links")
    def api_create_link():
        data = request.get_json(silent=True) or request.form
        try:
            link = links.create_link(db, data.get("url"), data.get("slug") or None, data.get("title"))
        except links.LinkError as e:
            return jsonify(error=str(e)), 400
        return jsonify(link), 201

    @app.get("/api/links")
    def api_list_links():
        return jsonify(links.list_links(db))

    @app.get("/api/links/<slug>")
    def api_get_link(slug):
        link = links.get_link(db, slug)
        if link is None:
            abort(404)
        return jsonify(link)

    @app.delete("/api/links/<slug>")
    def api_delete_link(slug):
        if not links.delete_link(db, slug):
            abort(404)
        if not analytics_client.delete_clicks(slug):
            return jsonify(warning="link deleted, but its clicks could not be removed yet"), 200
        return "", 204

    @app.get("/<slug>")
    def follow(slug):
        link = links.get_link(db, slug)
        if link is None:
            abort(404)
        # Cross seam call. If analytics is down the redirect still works, the click is just not counted.
        analytics_client.record_click(slug, request.referrer)
        return redirect(link["url"], code=302)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
