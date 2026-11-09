"""Mangas propios (guardados por scraper-manga en Supabase) servidos junto a los de MangaDex."""

import httpx

CIRCLES = {
    "id": "zonatmo-18536",
    "title": "Circles",
    "description": "¡Eres mi tipo!",
    "cover_url": "https://zonatmo.org/storage/proxy/c.jpg?v=2",
    "type": "manhwa",
    "status": None,
    "year": None,
    "tags": [],
}
CAP_1 = {
    "id": "zonatmo-18536~1",
    "number": "1",
    "title": None,
    "language": "es",
    "pages": 2,
    "external_url": None,
}
EMPTY = {"data": [], "total": 0}


def mangadex_with(total: int):
    """MangaDex falso con `total` resultados (ids md0, md1…) que respeta offset y limit."""

    def handler(request):
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        data = [
            {"id": f"md{i}", "attributes": {"title": {"en": f"M{i}"}}}
            for i in range(offset, min(offset + limit, total))
        ]
        return httpx.Response(200, json={"data": data, "total": total})

    return handler


def ids(res) -> list[str]:
    return [m["id"] for m in res.json()["items"]]


def test_search_puts_local_mangas_last(client, mangadex_routes, local_catalog):
    # Sin valoración ni popularidad, los propios van después de todo MangaDex.
    local_catalog.mangas = [CIRCLES]
    mangadex_routes["/manga"] = mangadex_with(1)
    res = client.get("/api/manga", params={"q": "circ"})
    assert ids(res) == ["md0", "zonatmo-18536"]
    assert res.json()["total"] == 2


def test_search_only_local_when_mangadex_has_nothing(client, mangadex_routes, local_catalog):
    local_catalog.mangas = [CIRCLES]
    mangadex_routes["/manga"] = EMPTY
    res = client.get("/api/manga", params={"q": "circ"})
    assert res.json() == {"items": [CIRCLES], "total": 1}


def test_search_local_mangas_go_on_the_last_page(client, mangadex_routes, local_catalog):
    local_catalog.mangas = [CIRCLES]
    mangadex_routes["/manga"] = mangadex_with(30)

    first = client.get("/api/manga", params={"limit": 24})
    assert "zonatmo-18536" not in ids(first)
    assert first.json()["total"] == 31  # cuenta los propios para que el scroll llegue a ellos

    last = client.get("/api/manga", params={"limit": 24, "offset": 24})
    assert ids(last) == [f"md{i}" for i in range(24, 30)] + ["zonatmo-18536"]


def test_search_local_mangas_alone_after_a_full_mangadex_page(
    client, mangadex_routes, local_catalog
):
    local_catalog.mangas = [CIRCLES]
    mangadex_routes["/manga"] = mangadex_with(24)
    assert "zonatmo-18536" not in ids(client.get("/api/manga", params={"limit": 24}))
    assert ids(client.get("/api/manga", params={"limit": 24, "offset": 24})) == ["zonatmo-18536"]


def test_search_filters_local_by_query_and_type(client, mangadex_routes, local_catalog):
    local_catalog.mangas = [CIRCLES]
    mangadex_routes["/manga"] = EMPTY
    assert client.get("/api/manga", params={"q": "otro"}).json()["items"] == []
    assert client.get("/api/manga", params={"type": "manga"}).json()["items"] == []
    assert client.get("/api/manga", params={"type": "manhwa"}).json()["items"] == [CIRCLES]


def test_search_skips_local_on_next_pages_and_unsupported_filters(
    client, mangadex_routes, local_catalog
):
    local_catalog.mangas = [CIRCLES]
    mangadex_routes["/manga"] = EMPTY
    for params in ({"offset": 24}, {"genre": "g1"}, {"status": "ongoing"}, {"lang": "en"}):
        assert client.get("/api/manga", params=params).json()["items"] == [], params


def test_search_still_works_if_local_catalog_fails(client, mangadex_routes, local_catalog):
    def boom(q, type):
        raise RuntimeError("db caída")

    local_catalog.search = boom
    mangadex_routes["/manga"] = EMPTY
    assert client.get("/api/manga").status_code == 200


def test_local_manga_chapters_and_pages(client, local_catalog):
    # mangadex_routes vacío: si se consultara MangaDex respondería 404
    local_catalog.mangas = [CIRCLES]
    local_catalog.chapters_by_manga = {"zonatmo-18536": [CAP_1]}
    local_catalog.pages_by_chapter = {"zonatmo-18536~1": ["https://storage.zonatmo.org/a.webp"]}

    assert client.get("/api/manga/zonatmo-18536").json() == CIRCLES
    assert client.get("/api/manga/zonatmo-18536/chapters").json() == {
        "items": [CAP_1],
        "total": 1,
        "unavailable": 0,
    }
    assert client.get("/api/chapters/zonatmo-18536~1/pages").json() == {
        "pages": ["https://storage.zonatmo.org/a.webp"]
    }


def test_unknown_local_ids_are_404(client):
    assert client.get("/api/manga/zonatmo-999").status_code == 404
    assert client.get("/api/manga/inmanga-x/chapters").status_code == 404
    assert client.get("/api/chapters/zonatmo-999~1/pages").status_code == 404


def test_image_proxy_is_only_for_mangadex(client):
    # zonatmo bloquea a Render; el frontend carga esas imágenes directo desde el navegador
    for url in ("https://storage2.zonatmo.org/x.webp", "https://cdn1.intomanga.com/x.jpg"):
        assert client.get("/api/image", params={"url": url}).status_code == 400, url
