from urllib.parse import urlparse


def normalise_referrer(referrer):
    if not referrer:
        return "direct"
    host = urlparse(referrer).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "direct"


def record_click(conn, slug, referrer=None):
    conn.execute(
        "INSERT INTO clicks (slug, referrer) VALUES (?, ?)",
        (slug, normalise_referrer(referrer)),
    )
    conn.commit()


def get_stats(conn, slug):
    total = conn.execute(
        "SELECT COUNT(*) FROM clicks WHERE slug = ?", (slug,)
    ).fetchone()[0]
    by_day = conn.execute(
        "SELECT date(clicked_at) AS day, COUNT(*) AS n FROM clicks "
        "WHERE slug = ? GROUP BY day ORDER BY day",
        (slug,),
    ).fetchall()
    by_referrer = conn.execute(
        "SELECT referrer, COUNT(*) AS n FROM clicks "
        "WHERE slug = ? GROUP BY referrer ORDER BY n DESC",
        (slug,),
    ).fetchall()
    return {
        "slug": slug,
        "total": total,
        "by_day": {r["day"]: r["n"] for r in by_day},
        "by_referrer": {r["referrer"]: r["n"] for r in by_referrer},
    }


def delete_clicks(conn, slug):
    conn.execute("DELETE FROM clicks WHERE slug = ?", (slug,))
    conn.commit()
