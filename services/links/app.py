import logging
import os
import time

from flask import Flask, abort, g, jsonify, redirect, request

import analytics_client
import service as links
from db import check, get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("links")
VERSION = os.environ.get("GIT_SHA", "dev")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")


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
        if request.headers.get("Origin") == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.get("/health")
    def health():
        ok = check(conn)
        body = {"status": "ok" if ok else "error", "db": "ok" if ok else "error", "version": VERSION}
        return jsonify(body), 200 if ok else 503

    @app.post("/api/links")
    def api_create_link():
        data = request.get_json(silent=True) or request.form
        try:
            link = links.create_link(conn, data.get("url"), data.get("slug") or None)
        except links.LinkError as e:
            return jsonify(error=str(e)), 400
        return jsonify(link), 201

    @app.get("/api/links")
    def api_list_links():
        return jsonify(links.list_links(conn))

    @app.get("/api/links/<slug>")
    def api_get_link(slug):
        link = links.get_link(conn, slug)
        if link is None:
            abort(404)
        return jsonify(link)

    @app.delete("/api/links/<slug>")
    def api_delete_link(slug):
        if not links.delete_link(conn, slug):
            abort(404)
        if not analytics_client.delete_clicks(slug):
            return jsonify(warning="link deleted, but its clicks could not be removed yet"), 200
        return "", 204

    @app.get("/<slug>")
    def follow(slug):
        link = links.get_link(conn, slug)
        if link is None:
            abort(404)
        # Cross seam call. If analytics is down the redirect still works, the click is just not counted.
        analytics_client.record_click(slug, request.referrer)
        return redirect(link["url"], code=302)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
