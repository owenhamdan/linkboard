import random
import re
import string
from urllib.parse import urlparse

import pymssql

SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,32}$")
SLUG_LENGTH = 6
COLUMNS = "id, slug, url, title, created_at"
TITLE_MAX = 255


class LinkError(ValueError):
    pass


def validate_url(url):
    if not url or not url.strip():
        raise LinkError("URL is required")
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise LinkError("URL must start with http:// or https://")
    if len(url) > 2048:
        raise LinkError("URL is too long")
    return url


def generate_slug(length=SLUG_LENGTH):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _to_dict(row):
    if row is None:
        return None
    link = dict(row)
    link["created_at"] = link["created_at"].isoformat()
    return link


def default_title(url):
    """Same rule as migration 002 uses for existing rows: the URL's host name."""
    return urlparse(url).netloc[:TITLE_MAX]


def create_link(db, url, slug=None, title=None):
    url = validate_url(url)
    title = (title or "").strip()[:TITLE_MAX] or default_title(url)
    if slug:
        if not SLUG_PATTERN.match(slug):
            raise LinkError("Slug must be 3 to 32 letters, digits or underscores")
    else:
        slug = generate_slug()
        while get_link(db, slug) is not None:
            slug = generate_slug()
    try:
        with db.cursor() as cur:
            cur.execute("INSERT INTO links (slug, url, title) VALUES (%s, %s, %s)", (slug, url, title))
    except pymssql.IntegrityError:
        raise LinkError("Slug already taken")
    return get_link(db, slug)


def get_link(db, slug):
    with db.cursor() as cur:
        cur.execute(f"SELECT {COLUMNS} FROM links WHERE slug = %s", (slug,))
        return _to_dict(cur.fetchone())


def list_links(db):
    with db.cursor() as cur:
        cur.execute(f"SELECT {COLUMNS} FROM links ORDER BY id DESC")
        return [_to_dict(r) for r in cur.fetchall()]


def delete_link(db, slug):
    with db.cursor() as cur:
        cur.execute("DELETE FROM links WHERE slug = %s", (slug,))
        return cur.rowcount > 0
