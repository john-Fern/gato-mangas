import httpx

MANGA = {
    "id": "m1",
    "attributes": {
        "title": {"ja-ro": "Ore no Manga"},
        "altTitles": [{"en": "My Manga"}],
        "description": {"en": "A story", "es": "Una historia"},
        "originalLanguage": "ko",
        "status": "ongoing",
        "year": 2020,
        "tags": [{"attributes": {"name": {"en": "Action"}}}],
    },
    "relationships": [
        {"type": "author", "id": "a1"},
        {"type": "cover_art", "attributes": {"fileName": "cover.jpg"}},
    ],
}


def test_search_normalizes_manga(client, mangadex_routes):
    seen = {}

    def handler(request):
        seen["params"] = request.url.params
        return httpx.Response(200, json={"data": [MANGA], "total": 1})

    mangadex_routes["/manga"] = handler
    res = client.get("/api/manga", params={"q": "ore"})

    assert res.status_code == 200
    assert seen["params"]["title"] == "ore"
    body = res.json()
    assert body["total"] == 1
    m = body["items"][0]
    assert m == {
        "id": "m1",
        "title": "My Manga",
        "description": "Una historia",
        "cover_url": "https://uploads.mangadex.org/covers/m1/cover.jpg.256.jpg",
        "type": "manhwa",
        "status": "ongoing",
        "year": 2020,
        "tags": ["Action"],
    }


def test_popular_without_query_orders_by_follows(client, mangadex_routes):
    seen = {}

    def handler(request):
        seen["params"] = request.url.params
        return httpx.Response(200, json={"data": [], "total": 0})

    mangadex_routes["/manga"] = handler
    res = client.get("/api/manga")

    assert res.status_code == 200
    assert "title" not in seen["params"]
    assert seen["params"]["order[followedCount]"] == "desc"


def test_get_manga_detail(client, mangadex_routes):
    mangadex_routes["/manga/m1"] = {"data": MANGA}
    res = client.get("/api/manga/m1")
    assert res.status_code == 200
    assert res.json()["title"] == "My Manga"


def test_get_manga_not_found(client):
    assert client.get("/api/manga/nope").status_code == 404


def test_chapters_filtered_by_language(client, mangadex_routes):
    seen = {}

    def handler(request):
        seen["langs"] = request.url.params.get_list("translatedLanguage[]")
        chapter = {
            "id": "c1",
            "attributes": {
                "chapter": "1",
                "title": "Inicio",
                "translatedLanguage": "es",
                "pages": 20,
                "externalUrl": None,
            },
        }
        return httpx.Response(200, json={"data": [chapter], "total": 1})

    mangadex_routes["/manga/m1/feed"] = handler
    res = client.get("/api/manga/m1/chapters", params={"lang": "es"})

    assert seen["langs"] == ["es"]
    assert res.json() == {
        "items": [
            {
                "id": "c1",
                "number": "1",
                "title": "Inicio",
                "language": "es",
                "pages": 20,
                "external_url": None,
            }
        ],
        "total": 1,
    }


def test_chapter_pages_are_proxied(client, mangadex_routes):
    mangadex_routes["/at-home/server/c1"] = {
        "baseUrl": "https://node.mangadex.network",
        "chapter": {"hash": "h", "data": ["1.png", "2.png"], "dataSaver": []},
    }
    res = client.get("/api/chapters/c1/pages")
    assert res.json() == {
        "pages": [
            "https://node.mangadex.network/data/h/1.png",
            "https://node.mangadex.network/data/h/2.png",
        ]
    }


def test_image_proxy_rejects_foreign_hosts(client):
    res = client.get("/api/image", params={"url": "https://evil.example.com/x.png"})
    assert res.status_code == 400


def test_image_proxy_streams_allowed_host(client, mangadex_routes):
    mangadex_routes["/covers/m1/cover.jpg"] = lambda r: httpx.Response(
        200, content=b"IMG", headers={"content-type": "image/jpeg"}
    )
    res = client.get(
        "/api/image", params={"url": "https://uploads.mangadex.org/covers/m1/cover.jpg"}
    )
    assert res.status_code == 200
    assert res.content == b"IMG"
    assert res.headers["content-type"] == "image/jpeg"
