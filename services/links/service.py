import random
import re
import string
import sqlite3

SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,32}$")
SLUG_LENGTH = 6


class LinkError(ValueError):
    pass


def validate_url(url):
    if not url or not url.strip():
        raise LinkError("URL is required")
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise LinkError("URL must start with http:// or https://")
    return url


def generate_slug(length=SLUG_LENGTH):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def create_link(conn, url, slug=None):
    url = validate_url(url)
    if slug:
        if not SLUG_PATTERN.match(slug):
            raise LinkError("Slug must be 3 to 32 letters, digits or underscores")
    else:
        slug = generate_slug()
        while get_link(conn, slug) is not None:
            slug = generate_slug()
    try:
        conn.execute("INSERT INTO links (slug, url) VALUES (?, ?)", (slug, url))
        conn.commit()
    except sqlite3.IntegrityError:
        raise LinkError("Slug already taken")
    return get_link(conn, slug)


def get_link(conn, slug):
    row = conn.execute("SELECT * FROM links WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


def list_links(conn):
    rows = conn.execute("SELECT * FROM links ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def delete_link(conn, slug):
    cur = conn.execute("DELETE FROM links WHERE slug = ?", (slug,))
    conn.commit()
    return cur.rowcount > 0
