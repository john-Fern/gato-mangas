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


def _chapter(id_, number, lang="es", external=None):
    return {
        "id": id_,
        "attributes": {
            "chapter": number,
            "title": None,
            "translatedLanguage": lang,
            "pages": 0 if external else 20,
            "externalUrl": external,
        },
    }


def test_spanish_includes_spain_and_latam(client, mangadex_routes):
    seen = {}

    def handler(request):
        seen["langs"] = request.url.params.get_list("translatedLanguage[]")
        return httpx.Response(200, json={"data": [_chapter("c1", "1")], "total": 1})

    mangadex_routes["/manga/m1/feed"] = handler
    res = client.get("/api/manga/m1/chapters", params={"lang": "es"})

    assert seen["langs"] == ["es", "es-la"]
    assert res.json() == {
        "items": [
            {
                "id": "c1",
                "number": "1",
                "title": None,
                "language": "es",
                "pages": 20,
                "external_url": None,
            }
        ],
        "total": 1,
    }


def test_chapters_fetch_every_page(client, mangadex_routes):
    all_chapters = [_chapter(f"c{i}", str(i)) for i in range(1, 1201)]

    def handler(request):
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        page = all_chapters[offset : offset + limit]
        return httpx.Response(200, json={"data": page, "total": len(all_chapters)})

    mangadex_routes["/manga/m1/feed"] = handler
    body = client.get("/api/manga/m1/chapters", params={"lang": "en"}).json()

    assert body["total"] == 1200
    assert [c["number"] for c in body["items"]][-1] == "1200"


def test_one_entry_per_chapter_preferring_readable(client, mangadex_routes):
    mangadex_routes["/manga/m1/feed"] = {
        "data": [
            _chapter("ext", "1", external="https://example.com/1"),
            _chapter("es1", "1"),
            _chapter("la1", "1", lang="es-la"),
            _chapter("o1", None),
            _chapter("o2", None),
            _chapter("ext2", "2", external="https://example.com/2"),
        ],
        "total": 6,
    }
    body = client.get("/api/manga/m1/chapters", params={"lang": "es"}).json()
    assert [c["id"] for c in body["items"]] == ["es1", "o1", "o2", "ext2"]


def test_unsupported_chapter_language_is_rejected(client):
    assert client.get("/api/manga/m1/chapters", params={"lang": "fr"}).status_code == 422


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


def test_root_points_to_docs(client):
    assert client.get("/").json() == {"name": "Gato Mangas API", "docs": "/docs"}


def _capture(mangadex_routes):
    seen = {}

    def handler(request):
        seen["params"] = request.url.params
        return httpx.Response(200, json={"data": [], "total": 0})

    mangadex_routes["/manga"] = handler
    return seen


def test_filter_by_type_maps_to_original_language(client, mangadex_routes):
    seen = _capture(mangadex_routes)
    client.get("/api/manga", params={"type": "manhua", "q": "x"})
    assert seen["params"].get_list("originalLanguage[]") == ["zh", "zh-hk"]


def test_without_type_does_not_filter_language(client, mangadex_routes):
    seen = _capture(mangadex_routes)
    client.get("/api/manga")
    assert seen["params"].get_list("originalLanguage[]") == []


def test_invalid_type_is_rejected(client):
    assert client.get("/api/manga", params={"type": "novela"}).status_code == 422


def test_pagination_params_are_forwarded(client, mangadex_routes):
    seen = _capture(mangadex_routes)
    client.get("/api/manga", params={"offset": 48, "limit": 24})
    assert (seen["params"]["offset"], seen["params"]["limit"]) == ("48", "24")


def test_all_filters_map_to_mangadex_params(client, mangadex_routes):
    seen = _capture(mangadex_routes)
    res = client.get(
        "/api/manga",
        params=[
            ("type", "manhwa"),
            ("genre", "g1"),
            ("genre", "g2"),
            ("status", "completed"),
            ("demographic", "seinen"),
            ("sort", "latest"),
            ("lang", "es"),
        ],
    )
    assert res.status_code == 200
    p = seen["params"]
    assert p.get_list("originalLanguage[]") == ["ko"]
    assert p.get_list("includedTags[]") == ["g1", "g2"]
    assert p.get_list("status[]") == ["completed"]
    assert p.get_list("publicationDemographic[]") == ["seinen"]
    assert p["order[latestUploadedChapter]"] == "desc"
    assert p.get_list("availableTranslatedLanguage[]") == ["es", "es-la"]


def test_query_sorts_by_relevance_by_default(client, mangadex_routes):
    seen = _capture(mangadex_routes)
    client.get("/api/manga", params={"q": "solo"})
    assert seen["params"]["order[relevance]"] == "desc"
    assert "order[followedCount]" not in seen["params"]


def test_explicit_sort_overrides_relevance(client, mangadex_routes):
    seen = _capture(mangadex_routes)
    client.get("/api/manga", params={"q": "solo", "sort": "rating"})
    assert seen["params"]["order[rating]"] == "desc"
    assert "order[relevance]" not in seen["params"]


def test_invalid_sort_is_rejected(client):
    assert client.get("/api/manga", params={"sort": "random"}).status_code == 422


def test_genres_lists_only_genres_in_spanish(client, mangadex_routes):
    def tag(id_, name, group):
        return {"id": id_, "attributes": {"name": {"en": name}, "group": group}}

    mangadex_routes["/manga/tag"] = {
        "data": [
            tag("t1", "Romance", "genre"),
            tag("t2", "Action", "genre"),
            tag("t3", "Zombies", "theme"),
            tag("t4", "Wuxia", "genre"),
        ]
    }
    assert client.get("/api/genres").json() == [
        {"id": "t2", "name": "Acción"},
        {"id": "t1", "name": "Romance"},
        {"id": "t4", "name": "Wuxia"},
    ]
