from urllib.parse import urlparse

REFERRER_MAX = 255


def normalise_referrer(referrer):
    if not referrer:
        return "direct"
    host = urlparse(referrer).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return (host or "direct")[:REFERRER_MAX]


def record_click(db, slug, referrer=None):
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO clicks (slug, referrer) VALUES (%s, %s)",
            (slug, normalise_referrer(referrer)),
        )


def get_stats(db, slug):
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM clicks WHERE slug = %s", (slug,))
        total = cur.fetchone()["n"]
        cur.execute(
            "SELECT CAST(clicked_at AS DATE) AS day, COUNT(*) AS n FROM clicks "
            "WHERE slug = %s GROUP BY CAST(clicked_at AS DATE) ORDER BY day",
            (slug,),
        )
        by_day = cur.fetchall()
        cur.execute(
            "SELECT referrer, COUNT(*) AS n FROM clicks "
            "WHERE slug = %s GROUP BY referrer ORDER BY n DESC",
            (slug,),
        )
        by_referrer = cur.fetchall()
    return {
        "slug": slug,
        "total": total,
        "by_day": {r["day"].isoformat(): r["n"] for r in by_day},
        "by_referrer": {r["referrer"]: r["n"] for r in by_referrer},
    }


def delete_clicks(db, slug):
    with db.cursor() as cur:
        cur.execute("DELETE FROM clicks WHERE slug = %s", (slug,))
