"""LocalCatalog contra Postgres real (tablas de supabase/migrations)."""

import psycopg
import pytest

from app.local import LocalCatalog
from app.mangadex import NotFound
from tests.conftest import DATABASE_URL


@pytest.fixture
def catalog(db):
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute(
            "insert into mangas (id, source, title, type, url, cover_url, description) values"
            " ('zonatmo-1', 'zonatmo', 'Circles', 'manhwa', 'u', 'c.jpg', 'desc'),"
            " ('inmanga-2', 'inmanga', 'Monster', 'manga', 'u', null, null),"
            " ('zonatmo-3', 'zonatmo', 'Raro', 'doujinshi', 'u', null, null)"
        )
        conn.execute(
            "insert into chapters (manga_id, number, title, source_url, image_urls) values"
            " ('zonatmo-1', 10, 'Capítulo 10', 's', array['a','b','c']),"
            " ('zonatmo-1', 1.5, 'El comienzo', 's', array['x']),"
            " ('zonatmo-1', 2, 'Capítulo 2', 's', array['p1','p2'])"
        )
    return LocalCatalog(lambda: psycopg.connect(DATABASE_URL))


def test_search(catalog):
    assert [m["id"] for m in catalog.search(None, None)] == ["zonatmo-1", "inmanga-2", "zonatmo-3"]
    assert [m["id"] for m in catalog.search("circ", None)] == ["zonatmo-1"]
    assert [m["id"] for m in catalog.search(None, "manga")] == ["inmanga-2"]


def test_manga_normalized_like_mangadex(catalog):
    assert catalog.manga("zonatmo-1") == {
        "id": "zonatmo-1",
        "title": "Circles",
        "description": "desc",
        "cover_url": "c.jpg",
        "type": "manhwa",
        "status": None,
        "year": None,
        "tags": [],
    }
    assert catalog.manga("zonatmo-3")["type"] == "other"


def test_chapters_sorted_with_ids(catalog):
    body = catalog.chapters("zonatmo-1")
    assert body["total"] == 3 and body["unavailable"] == 0
    assert [(c["id"], c["number"], c["title"], c["pages"]) for c in body["items"]] == [
        ("zonatmo-1~1.5", "1.5", "El comienzo", 1),
        ("zonatmo-1~2", "2", None, 2),  # "Capítulo 2" no aporta nada al lado del número
        ("zonatmo-1~10", "10", None, 3),
    ]


def test_pages(catalog):
    assert catalog.pages("zonatmo-1~2") == ["p1", "p2"]
    assert catalog.pages("zonatmo-1~1.5") == ["x"]


def test_not_found(catalog):
    for call in (
        lambda: catalog.manga("zonatmo-9"),
        lambda: catalog.chapters("zonatmo-9"),
        lambda: catalog.pages("zonatmo-1~99"),
        lambda: catalog.pages("zonatmo-1~abc"),
    ):
        with pytest.raises(NotFound):
            call()
