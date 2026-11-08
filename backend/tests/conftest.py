import os
from pathlib import Path

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient

from app import main
from app.mangadex import MangaDexClient

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/manga_test"
)
MIGRATIONS = Path(__file__).parents[2] / "supabase" / "migrations"
USER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mangadex_routes():
    """Diccionario path -> respuesta JSON (o callable(request) -> httpx.Response)."""
    return {}


@pytest.fixture
def client(mangadex_routes, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        route = mangadex_routes.get(request.url.path)
        if route is None:
            return httpx.Response(404, json={"result": "error"})
        if callable(route):
            return route(request)
        return httpx.Response(200, json=route)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    main.app.dependency_overrides[main.get_mangadex] = lambda: MangaDexClient(http)
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def db():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("drop table if exists favorites, reading_progress")
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
