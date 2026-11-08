"""Cliente mínimo de la API pública de MangaDex que normaliza las respuestas."""

import httpx

API_URL = "https://api.mangadex.org"
COVERS_URL = "https://uploads.mangadex.org/covers"
TYPES = {"ja": "manga", "ko": "manhwa", "zh": "manhua", "zh-hk": "manhua"}
LANGS_BY_TYPE = {t: [lang for lang, x in TYPES.items() if x == t] for t in set(TYPES.values())}
SORTS = {
    "relevance": ("relevance", "desc"),
    "popular": ("followedCount", "desc"),
    "latest": ("latestUploadedChapter", "desc"),
    "rating": ("rating", "desc"),
    "new": ("createdAt", "desc"),
    "title": ("title", "asc"),
}
GENRES_ES = {
    "Action": "Acción",
    "Adventure": "Aventura",
    "Boys' Love": "Boys' Love (BL)",
    "Comedy": "Comedia",
    "Crime": "Crimen",
    "Drama": "Drama",
    "Fantasy": "Fantasía",
    "Girls' Love": "Girls' Love (GL)",
    "Historical": "Histórico",
    "Horror": "Terror",
    "Isekai": "Isekai",
    "Magical Girls": "Chicas mágicas",
    "Mecha": "Mecha",
    "Medical": "Médico",
    "Mystery": "Misterio",
    "Philosophical": "Filosófico",
    "Psychological": "Psicológico",
    "Romance": "Romance",
    "Sci-Fi": "Ciencia ficción",
    "Slice of Life": "Recuentos de la vida",
    "Sports": "Deportes",
    "Superhero": "Superhéroes",
    "Thriller": "Suspenso",
    "Tragedy": "Tragedia",
    "Wuxia": "Wuxia",
}
CONTENT_RATINGS = ["safe", "suggestive"]
PREFERRED_LANGS = ["es", "es-la", "en"]


class NotFound(Exception):
    pass


def _pick(texts: dict, langs=PREFERRED_LANGS) -> str | None:
    for lang in langs:
        if texts.get(lang):
            return texts[lang]
    return next(iter(texts.values()), None)


def normalize_manga(data: dict) -> dict:
    attrs = data["attributes"]
    title = attrs["title"].get("en")
    if not title:
        alt = next((t for t in attrs.get("altTitles", []) if "en" in t), None)
        title = alt["en"] if alt else _pick(attrs["title"])
    cover = next((r for r in data.get("relationships", []) if r["type"] == "cover_art"), None)
    file_name = (cover or {}).get("attributes", {}).get("fileName")
    return {
        "id": data["id"],
        "title": title,
        "description": _pick(attrs.get("description") or {}),
        "cover_url": f"{COVERS_URL}/{data['id']}/{file_name}.256.jpg" if file_name else None,
        "type": TYPES.get(attrs.get("originalLanguage"), "other"),
        "status": attrs.get("status"),
        "year": attrs.get("year"),
        "tags": [_pick(t["attributes"]["name"]) for t in attrs.get("tags", [])],
    }


def normalize_chapter(data: dict) -> dict:
    attrs = data["attributes"]
    return {
        "id": data["id"],
        "number": attrs.get("chapter"),
        "title": attrs.get("title"),
        "language": attrs.get("translatedLanguage"),
        "pages": attrs.get("pages"),
        "external_url": attrs.get("externalUrl"),
    }


class MangaDexClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def _get(self, path: str, params=None) -> dict:
        res = await self.http.get(f"{API_URL}{path}", params=params)
        if res.status_code == 404:
            raise NotFound(path)
        res.raise_for_status()
        return res.json()

    async def search(self, f) -> dict:
        """`f` es un MangaFilters (ver main.py)."""
        params: dict = {
            "limit": f.limit,
            "offset": f.offset,
            "includes[]": "cover_art",
            "contentRating[]": CONTENT_RATINGS,
        }
        if f.q:
            params["title"] = f.q
        if f.type:
            params["originalLanguage[]"] = LANGS_BY_TYPE[f.type]
        if f.genre:
            params["includedTags[]"] = f.genre
        if f.status:
            params["status[]"] = [f.status]
        if f.demographic:
            params["publicationDemographic[]"] = [f.demographic]
        if f.lang:
            params["availableTranslatedLanguage[]"] = [f.lang]
        field, direction = SORTS[f.sort or ("relevance" if f.q else "popular")]
        params[f"order[{field}]"] = direction
        body = await self._get("/manga", params)
        return {"items": [normalize_manga(m) for m in body["data"]], "total": body["total"]}

    async def genres(self) -> list[dict]:
        body = await self._get("/manga/tag")
        genres = [
            {"id": t["id"], "name": GENRES_ES.get(name, name)}
            for t in body["data"]
            if t["attributes"]["group"] == "genre"
            for name in [t["attributes"]["name"]["en"]]
        ]
        return sorted(genres, key=lambda g: g["name"])

    async def manga(self, manga_id: str) -> dict:
        body = await self._get(f"/manga/{manga_id}", {"includes[]": "cover_art"})
        return normalize_manga(body["data"])

    async def chapters(self, manga_id: str, lang: str, limit: int, offset: int) -> dict:
        params = {
            "translatedLanguage[]": [lang],
            "order[chapter]": "asc",
            "limit": limit,
            "offset": offset,
            "contentRating[]": CONTENT_RATINGS,
        }
        body = await self._get(f"/manga/{manga_id}/feed", params)
        return {"items": [normalize_chapter(c) for c in body["data"]], "total": body["total"]}

    async def pages(self, chapter_id: str) -> list[str]:
        body = await self._get(f"/at-home/server/{chapter_id}")
        base, ch = body["baseUrl"], body["chapter"]
        return [f"{base}/data/{ch['hash']}/{f}" for f in ch["data"]]

    async def image(self, url: str) -> httpx.Response:
        return await self.http.get(url, headers={"Referer": "https://mangadex.org/"})
