"""Tests del apartado de descarga/importación de mangas (ZonaTMO e InManga)."""

import json

import httpx
import pytest

from app import main
from app.local import LocalCatalog
from app.scraper import ScraperClient
from tests.conftest import USER_ID

TMO_ID = "1682"
TMO_URL = f"https://zonatmo.org/library/manga/{TMO_ID}/gachiakuta"
INMANGA_ID = "be792685-a03f-4ac6-94c3-d9149c12f808"
INMANGA_URL = f"https://inmanga.com/ver/manga/Monster/{INMANGA_ID}"

TMO_SUGGEST = [
    {
        "id": 1682,
        "title": "Gachiakuta",
        "slug": "gachiakuta",
        "type": "manga",
        "url": TMO_URL,
    },
    {
        "id": 18536,
        "title": "Circles",
        "slug": "circles",
        "type": "manhwa",
        "url": "https://zonatmo.org/library/manhwa/18536/circles",
    },
]

TMO_OBRA_HTML = """
<img class="book-thumbnail" src="https://zonatmo.org/storage/proxy/gachi.jpg" alt="Gachiakuta">
<h1 class="element-title my-2">Gachiakuta</h1>
<p class="element-description" id="manga-synopsis">Un chico cae al abismo.</p>
<ul class="list-group list-chapters" id="chapters-list">
  <li class="list-group-item upload-link">
    <h4><span class="chapter-number">Capítulo 2</span></h4>
    <div class="chapter-detail"><a href="https://zonatmo.org/view_uploads/22">Leer</a></div>
  </li>
  <li class="list-group-item upload-link">
    <h4><span class="chapter-number">Capítulo 1</span></h4>
    <div class="chapter-detail"><a href="https://zonatmo.org/view_uploads/11">Leer</a></div>
  </li>
</ul>
"""

TMO_VISOR_HTML = """
<div id="reader-wrap">
  <img src="https://storage2.zonatmo.org/chapters/22/1.webp" class="reader-image">
  <img src="https://storage2.zonatmo.org/chapters/22/2.webp" class="reader-image">
</div>
"""

INMANGA_SEARCH_HTML = f"""
<a class="manga-result" href="/ver/manga/Monster/{INMANGA_ID}"><h4>Monster</h4></a>
"""

INMANGA_CHAPTERS_JSON = {
    "data": json.dumps(
        {
            "result": [
                {
                    "Number": 1.0,
                    "FriendlyChapterNumberUrl": "01",
                    "Identification": "cap-uuid-1",
                },
                {
                    "Number": 2.0,
                    "FriendlyChapterNumberUrl": "02",
                    "Identification": "cap-uuid-2",
                },
            ]
        }
    )
}

INMANGA_VIEWER_HTML = """
<script>var pu = 'https://pack-yak.intomanga.com/images/manga/Monster/chapter/pageNumber/page/identification';</script>
"""

INMANGA_CONTROLS_HTML = """
<select id="PageList">
  <option value="p-two">2</option>
  <option value="p-one">1</option>
</select>
"""


@pytest.fixture
def scraper_routes():
    return {}


@pytest.fixture
def scraper_client(client, scraper_routes):
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.host}{request.url.path}"
        route = scraper_routes.get(key) or scraper_routes.get(
            f"{request.url.host}{request.url.path}"
        )
        if route is None:
            return httpx.Response(404, text="not found")
        if callable(route):
            return route(request)
        if isinstance(route, str):
            return httpx.Response(200, text=route)
        return httpx.Response(200, json=route)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    main.app.dependency_overrides[main.get_user_id] = lambda: USER_ID
    main.app.dependency_overrides[main.get_scraper] = lambda: ScraperClient(http)
    return client


def test_scraper_requires_auth(client):
    assert client.get("/api/scraper/search", params={"q": "monster"}).status_code == 401
    assert client.post("/api/scraper/import", json={"url": TMO_URL}).status_code == 401


def test_search_by_direct_url_zonatmo_and_inmanga(scraper_client):
    res_tmo = scraper_client.get("/api/scraper/search", params={"q": TMO_URL})
    assert res_tmo.status_code == 200
    assert res_tmo.json() == {
        "items": [
            {
                "id": TMO_ID,
                "source": "zonatmo",
                "title": "gachiakuta",
                "type": "manga",
                "url": TMO_URL,
            }
        ]
    }

    res_im = scraper_client.get("/api/scraper/search", params={"q": INMANGA_URL})
    assert res_im.status_code == 200
    assert res_im.json() == {
        "items": [
            {
                "id": INMANGA_ID,
                "source": "inmanga",
                "title": "Monster",
                "type": "manga",
                "url": INMANGA_URL,
            }
        ]
    }


def test_search_by_name_zonatmo(scraper_client, scraper_routes):
    scraper_routes["zonatmo.org/api/search/suggest"] = TMO_SUGGEST
    res = scraper_client.get("/api/scraper/search", params={"q": "gachi", "source": "zonatmo"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2
    assert items[0] == {
        "id": "1682",
        "source": "zonatmo",
        "title": "Gachiakuta",
        "type": "manga",
        "url": TMO_URL,
    }
    assert items[1]["type"] == "manhwa"


def test_search_by_name_inmanga(scraper_client, scraper_routes):
    scraper_routes["POST inmanga.com/manga/getMangasConsultResult"] = INMANGA_SEARCH_HTML
    res = scraper_client.get("/api/scraper/search", params={"q": "monster", "source": "inmanga"})
    assert res.status_code == 200
    assert res.json() == {
        "items": [
            {
                "id": INMANGA_ID,
                "source": "inmanga",
                "title": "Monster",
                "type": "manga",
                "url": INMANGA_URL,
            }
        ]
    }


def test_import_rejects_invalid_url(scraper_client):
    res = scraper_client.post("/api/scraper/import", json={"url": "https://evil.example.com/manga"})
    assert res.status_code == 400


def test_import_zonatmo_saves_manga_and_skips_existing_chapters(
    scraper_client, scraper_routes, local_catalog
):
    # Pre-cargamos el capítulo 1 para verificar que se omite
    local_catalog.save_manga(
        {
            "id": f"zonatmo-{TMO_ID}",
            "source": "zonatmo",
            "title": "Gachiakuta",
            "type": "manga",
            "url": TMO_URL,
        }
    )
    local_catalog.save_chapter(
        {
            "manga_id": f"zonatmo-{TMO_ID}",
            "number": 1.0,
            "title": "Capítulo 1",
            "source_url": "https://zonatmo.org/view_uploads/11",
            "image_urls": ["https://storage2.zonatmo.org/chapters/11/1.webp"],
        }
    )

    scraper_routes[f"zonatmo.org/library/manga/{TMO_ID}/gachiakuta"] = TMO_OBRA_HTML
    scraper_routes["zonatmo.org/view_uploads/22"] = TMO_VISOR_HTML

    res = scraper_client.post("/api/scraper/import", json={"url": TMO_URL})
    assert res.status_code == 200
    assert res.json() == {
        "manga_id": f"zonatmo-{TMO_ID}",
        "title": "Gachiakuta",
        "imported": 1,
        "skipped": 1,
        "failed": 0,
    }

    manga = local_catalog.manga(f"zonatmo-{TMO_ID}")
    assert manga["title"] == "Gachiakuta"
    assert manga["cover_url"] == "https://zonatmo.org/storage/proxy/gachi.jpg"
    assert manga["description"] == "Un chico cae al abismo."
    assert local_catalog.pages(f"zonatmo-{TMO_ID}~2") == [
        "https://storage2.zonatmo.org/chapters/22/1.webp",
        "https://storage2.zonatmo.org/chapters/22/2.webp",
    ]


def test_import_inmanga_saves_available_chapters(scraper_client, scraper_routes, local_catalog):
    scraper_routes["inmanga.com/chapter/getall"] = INMANGA_CHAPTERS_JSON
    scraper_routes["inmanga.com/ver/manga/Monster/01/cap-uuid-1"] = INMANGA_VIEWER_HTML
    scraper_routes["inmanga.com/ver/manga/Monster/02/cap-uuid-2"] = INMANGA_VIEWER_HTML
    scraper_routes["inmanga.com/chapter/chapterIndexControls"] = INMANGA_CONTROLS_HTML
    # El capítulo 1 responde con imagen válida (>100 bytes), el 2 falla
    scraper_routes["pack-yak.intomanga.com/images/manga/Monster/chapter/1/page/p-one"] = lambda r: (
        httpx.Response(200, content=b"X" * 200)
    )

    res = scraper_client.post("/api/scraper/import", json={"url": INMANGA_URL, "to_chapter": 1})
    assert res.status_code == 200
    assert res.json() == {
        "manga_id": f"inmanga-{INMANGA_ID}",
        "title": "Monster",
        "imported": 1,
        "skipped": 0,
        "failed": 0,
    }
    assert local_catalog.pages(f"inmanga-{INMANGA_ID}~1") == [
        "https://pack-yak.intomanga.com/images/manga/Monster/chapter/1/page/p-one",
        "https://pack-yak.intomanga.com/images/manga/Monster/chapter/2/page/p-two",
    ]


def test_import_zonatmo_only_downloads_chapter_range(scraper_client, scraper_routes, local_catalog):
    scraper_routes[f"zonatmo.org/library/manga/{TMO_ID}/gachiakuta"] = TMO_OBRA_HTML
    scraper_routes["zonatmo.org/view_uploads/22"] = TMO_VISOR_HTML
    # Si se pidiera el capítulo 1, fallaría (no hay ruta) y contaría como "failed"

    res = scraper_client.post(
        "/api/scraper/import", json={"url": TMO_URL, "from_chapter": 2, "to_chapter": 2}
    )
    assert res.status_code == 200
    assert res.json() == {
        "manga_id": f"zonatmo-{TMO_ID}",
        "title": "Gachiakuta",
        "imported": 1,
        "skipped": 0,
        "failed": 0,
    }
    assert local_catalog.existing_chapters(f"zonatmo-{TMO_ID}") == {2.0}


def test_import_inmanga_from_chapter_only(scraper_client, scraper_routes, local_catalog):
    scraper_routes["inmanga.com/chapter/getall"] = INMANGA_CHAPTERS_JSON
    scraper_routes["inmanga.com/ver/manga/Monster/02/cap-uuid-2"] = INMANGA_VIEWER_HTML
    scraper_routes["inmanga.com/chapter/chapterIndexControls"] = INMANGA_CONTROLS_HTML
    scraper_routes["pack-yak.intomanga.com/images/manga/Monster/chapter/1/page/p-one"] = lambda r: (
        httpx.Response(200, content=b"X" * 200)
    )

    res = scraper_client.post("/api/scraper/import", json={"url": INMANGA_URL, "from_chapter": 2})
    assert res.status_code == 200
    assert res.json()["imported"] == 1
    assert local_catalog.existing_chapters(f"inmanga-{INMANGA_ID}") == {2.0}


def test_import_rejects_inverted_range(scraper_client):
    res = scraper_client.post(
        "/api/scraper/import", json={"url": TMO_URL, "from_chapter": 5, "to_chapter": 2}
    )
    assert res.status_code == 422


def test_local_catalog_sql_methods():
    executed: list[tuple[str, object]] = []

    class FakeCursor:
        def execute(self, sql, params):
            executed.append((sql, params))
            return self

        def fetchall(self):
            return [{"number": "1.0"}, {"number": "2.5"}]

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def cursor(self, **kw):
            return FakeCursor()

        def execute(self, sql, params):
            executed.append((sql, params))

        def commit(self):
            executed.append(("COMMIT", None))

    cat = LocalCatalog(FakeConn)  # type: ignore[arg-type]
    assert cat.existing_chapters("zonatmo-1") == {1.0, 2.5}
    cat.save_manga(
        {
            "id": "zonatmo-1",
            "source": "zonatmo",
            "title": "Circles",
            "type": "manhwa",
            "url": "https://zonatmo.org/library/manhwa/1/circles",
            "cover_url": None,
            "description": None,
        }
    )
    cat.save_chapter(
        {
            "manga_id": "zonatmo-1",
            "number": 1.0,
            "title": "Capítulo 1",
            "source_url": "https://zonatmo.org/view_uploads/1",
            "image_urls": ["https://img/1.webp"],
        }
    )
    assert any("insert into mangas" in s for s, _ in executed)
    assert any("insert into chapters" in s for s, _ in executed)
    assert executed.count(("COMMIT", None)) == 2
