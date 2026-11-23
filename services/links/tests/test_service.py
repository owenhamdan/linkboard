import pytest

import service as links


def test_create_with_custom_slug(db):
    link = links.create_link(db, "https://ie.edu", "iex")
    assert link["slug"] == "iex"
    assert link["url"] == "https://ie.edu"


def test_create_generates_slug(db):
    link = links.create_link(db, "https://ie.edu")
    assert len(link["slug"]) == links.SLUG_LENGTH


def test_rejects_bad_url(db):
    with pytest.raises(links.LinkError):
        links.create_link(db, "ftp://nope")
    with pytest.raises(links.LinkError):
        links.create_link(db, "  ")


def test_rejects_bad_slug(db):
    with pytest.raises(links.LinkError):
        links.create_link(db, "https://ie.edu", "a b")


def test_rejects_duplicate_slug(db):
    links.create_link(db, "https://ie.edu", "iex")
    with pytest.raises(links.LinkError):
        links.create_link(db, "https://other.com", "iex")


def test_list_and_delete(db):
    links.create_link(db, "https://a.com", "aaa")
    links.create_link(db, "https://b.com", "bbb")
    assert len(links.list_links(db)) == 2
    assert links.delete_link(db, "aaa") is True
    assert links.delete_link(db, "aaa") is False
    assert links.get_link(db, "aaa") is None
