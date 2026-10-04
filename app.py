import os

from flask import Flask, abort, jsonify, redirect, render_template, request

from analytics import service as analytics
from db import get_connection
from links import service as links


def create_app(db_path=None):
    app = Flask(__name__)
    conn = get_connection(db_path)

    @app.get("/")
    def index():
        return render_template("index.html", links=links.list_links(conn))

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

    @app.delete("/api/links/<slug>")
    def api_delete_link(slug):
        if not links.delete_link(conn, slug):
            abort(404)
        analytics.delete_clicks(conn, slug)
        return "", 204

    @app.get("/api/links/<slug>/stats")
    def api_stats(slug):
        if links.get_link(conn, slug) is None:
            abort(404)
        return jsonify(analytics.get_stats(conn, slug))

    @app.get("/<slug>")
    def follow(slug):
        link = links.get_link(conn, slug)
        if link is None:
            abort(404)
        analytics.record_click(conn, slug, request.referrer)
        return redirect(link["url"], code=302)

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)
