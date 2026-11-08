import os
from pathlib import Path

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient

from app import main
from app.mangadex import MangaDexClient, NotFound

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/manga_test"
)
MIGRATIONS = Path(__file__).parents[2] / "supabase" / "migrations"
USER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mangadex_routes():
    """Diccionario path -> respuesta JSON (o callable(request) -> httpx.Response)."""
    return {}


class FakeCatalog:
    """Catálogo local en memoria (el real, app.local.LocalCatalog, se prueba en test_local_db)."""

    def __init__(self):
        self.mangas: list[dict] = []
        self.chapters_by_manga: dict[str, list[dict]] = {}
        self.pages_by_chapter: dict[str, list[str]] = {}

    def search(self, q, type):
        return [
            m
            for m in self.mangas
            if (not q or q.lower() in m["title"].lower()) and (not type or m["type"] == type)
        ]

    def manga(self, manga_id):
        for m in self.mangas:
            if m["id"] == manga_id:
                return m
        raise NotFound(manga_id)

    def chapters(self, manga_id):
        self.manga(manga_id)
        items = self.chapters_by_manga.get(manga_id, [])
        return {"items": items, "total": len(items), "unavailable": 0}

    def pages(self, chapter_id):
        if chapter_id not in self.pages_by_chapter:
            raise NotFound(chapter_id)
        return self.pages_by_chapter[chapter_id]


@pytest.fixture
def local_catalog():
    return FakeCatalog()


@pytest.fixture
def client(mangadex_routes, local_catalog, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        route = mangadex_routes.get(request.url.path)
        if route is None:
            return httpx.Response(404, json={"result": "error"})
        if callable(route):
            return route(request)
        return httpx.Response(200, json=route)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    main.app.dependency_overrides[main.get_mangadex] = lambda: MangaDexClient(http)
    main.app.dependency_overrides[main.get_catalog] = lambda: local_catalog
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def db():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("drop table if exists favorites, reading_progress, chapters, mangas")
        for sql in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(sql.read_text())
    main.app.dependency_overrides[main.get_conn] = _conn
    yield


def _conn():
    with psycopg.connect(DATABASE_URL) as conn:
        yield conn


@pytest.fixture
def auth_client(client, db):
    main.app.dependency_overrides[main.get_user_id] = lambda: USER_ID
    return client
