import pytest

from db import get_connection
from links import service as links


@pytest.fixture
def conn():
    return get_connection(":memory:")


def test_create_with_custom_slug(conn):
    link = links.create_link(conn, "https://ie.edu", "iex")
    assert link["slug"] == "iex"
    assert link["url"] == "https://ie.edu"


def test_create_generates_slug(conn):
    link = links.create_link(conn, "https://ie.edu")
    assert len(link["slug"]) == links.SLUG_LENGTH


def test_rejects_bad_url(conn):
    with pytest.raises(links.LinkError):
        links.create_link(conn, "ftp://nope")
    with pytest.raises(links.LinkError):
        links.create_link(conn, "  ")


def test_rejects_bad_slug(conn):
    with pytest.raises(links.LinkError):
        links.create_link(conn, "https://ie.edu", "a b")


def test_rejects_duplicate_slug(conn):
    links.create_link(conn, "https://ie.edu", "iex")
    with pytest.raises(links.LinkError):
        links.create_link(conn, "https://other.com", "iex")


def test_list_and_delete(conn):
    links.create_link(conn, "https://a.com", "aaa")
    links.create_link(conn, "https://b.com", "bbb")
    assert len(links.list_links(conn)) == 2
    assert links.delete_link(conn, "aaa") is True
    assert links.delete_link(conn, "aaa") is False
    assert links.get_link(conn, "aaa") is None
