import logging
import os
from collections.abc import AsyncIterator, Iterator
from typing import Annotated, Literal
from urllib.parse import urlparse

import httpx
import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, model_validator

from app.local import LocalCatalog, is_local
from app.mangadex import MangaDexClient, NotFound
from app.scraper import InvalidMangaUrl, ScraperClient

app = FastAPI(title="Gato Mangas API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

log = logging.getLogger(__name__)
USER_AGENT = "gato-mangas/0.1"
_http = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT})


# ---------- dependencias ----------


async def get_mangadex() -> AsyncIterator[MangaDexClient]:
    yield MangaDexClient(_http)


async def get_scraper() -> AsyncIterator[ScraperClient]:
    yield ScraperClient(_http)


def get_conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        yield conn


def get_catalog() -> LocalCatalog:
    return LocalCatalog(lambda: psycopg.connect(os.environ["DATABASE_URL"]))


async def get_user_id(authorization: str | None = Header(default=None)) -> str:
    """Valida el token de Supabase Auth preguntándole a Supabase quién es el usuario."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Falta token")
    res = await _http.get(
        f"{os.environ['SUPABASE_URL']}/auth/v1/user",
        headers={"Authorization": authorization, "apikey": os.environ["SUPABASE_ANON_KEY"]},
    )
    if res.status_code != 200:
        raise HTTPException(401, "Token inválido")
    return res.json()["id"]


# ---------- catálogo (MangaDex) ----------


@app.exception_handler(NotFound)
async def not_found(_, __):
    return Response(status_code=404)


@app.get("/")
def root():
    return {"name": "Gato Mangas API", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


class MangaFilters(BaseModel):
    q: str | None = None
    type: Literal["manga", "manhwa", "manhua"] | None = None
    genre: list[str] = []
    status: Literal["ongoing", "completed", "hiatus", "cancelled"] | None = None
    demographic: Literal["shounen", "shoujo", "seinen", "josei"] | None = None
    sort: Literal["relevance", "popular", "latest", "rating", "new", "title"] | None = None
    lang: Literal["es", "en"] | None = None
    limit: int = Field(24, le=100)
    offset: int = Field(0, ge=0, le=9900)  # MangaDex no pagina más allá de 10.000


@app.get("/api/manga")
async def search(
    filters: Annotated[MangaFilters, Query()],
    md: MangaDexClient = Depends(get_mangadex),
    catalog: LocalCatalog = Depends(get_catalog),
):
    result = await md.search(filters)
    # Los mangas propios no tienen valoración ni popularidad: van al final, después de todo
    # MangaDex, y solo con los filtros que entienden. El total los cuenta para que el scroll llegue.
    unsupported = filters.genre or filters.status or filters.demographic or filters.lang == "en"
    if unsupported:
        return result
    try:
        local = catalog.search(filters.q, filters.type)
    except Exception:
        log.exception("No se pudo buscar en el catálogo propio")
        local = []
    start = filters.offset - result["total"]  # posición de esta página dentro de los propios
    page = local[max(start, 0) : max(start + filters.limit, 0)]
    return {"items": result["items"] + page, "total": result["total"] + len(local)}


_genres_cache: list[dict] = []


@app.get("/api/genres")
async def genres(md: MangaDexClient = Depends(get_mangadex)):
    # Los géneros de MangaDex casi nunca cambian: se piden una vez por proceso.
    if not _genres_cache:
        _genres_cache.extend(await md.genres())
    return _genres_cache


@app.get("/api/manga/{manga_id}")
async def manga(
    manga_id: str,
    md: MangaDexClient = Depends(get_mangadex),
    catalog: LocalCatalog = Depends(get_catalog),
):
    if is_local(manga_id):
        return catalog.manga(manga_id)
    return await md.manga(manga_id)


@app.get("/api/manga/{manga_id}/chapters")
async def chapters(
    manga_id: str,
    lang: Literal["es", "en"] = "es",
    md: MangaDexClient = Depends(get_mangadex),
    catalog: LocalCatalog = Depends(get_catalog),
):
    if is_local(manga_id):
        return catalog.chapters(manga_id)
    return await md.chapters(manga_id, lang)


@app.get("/api/chapters/{chapter_id}/pages")
async def pages(
    chapter_id: str,
    md: MangaDexClient = Depends(get_mangadex),
    catalog: LocalCatalog = Depends(get_catalog),
):
    if is_local(chapter_id):
        return {"pages": catalog.pages(chapter_id)}
    return {"pages": await md.pages(chapter_id)}


def _allowed_image_host(url: str) -> bool:
    p = urlparse(url)
    host = p.hostname or ""
    return p.scheme == "https" and (
        host == "uploads.mangadex.org" or host.endswith(".mangadex.network")
    )


@app.get("/api/image")
async def image(url: str, md: MangaDexClient = Depends(get_mangadex)):
    if not _allowed_image_host(url):
        raise HTTPException(400, "Host no permitido")
    res = await md.image(url)
    if res.status_code != 200:
        raise HTTPException(502, "No se pudo obtener la imagen")
    return Response(
        res.content,
        media_type=res.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ---------- datos del usuario (PostgreSQL / Supabase) ----------


class FavoriteIn(BaseModel):
    title: str
    cover_url: str | None = None


class ProgressIn(BaseModel):
    chapter_id: str
    chapter_number: str | None = None


@app.get("/api/me/favorites")
def list_favorites(user_id: str = Depends(get_user_id), conn=Depends(get_conn)):
    cur = conn.cursor(row_factory=dict_row)
    return cur.execute(
        "select manga_id, title, cover_url from favorites where user_id = %s"
        " order by created_at desc",
        (user_id,),
    ).fetchall()


@app.put("/api/me/favorites/{manga_id}", status_code=204)
def add_favorite(
    manga_id: str, fav: FavoriteIn, user_id: str = Depends(get_user_id), conn=Depends(get_conn)
):
    conn.execute(
        "insert into favorites (user_id, manga_id, title, cover_url) values (%s, %s, %s, %s)"
        " on conflict (user_id, manga_id) do update"
        " set title = excluded.title, cover_url = excluded.cover_url",
        (user_id, manga_id, fav.title, fav.cover_url),
    )
    conn.commit()


@app.delete("/api/me/favorites/{manga_id}", status_code=204)
def remove_favorite(manga_id: str, user_id: str = Depends(get_user_id), conn=Depends(get_conn)):
    conn.execute("delete from favorites where user_id = %s and manga_id = %s", (user_id, manga_id))
    conn.commit()


@app.get("/api/me/progress/{manga_id}")
def get_progress(manga_id: str, user_id: str = Depends(get_user_id), conn=Depends(get_conn)):
    cur = conn.cursor(row_factory=dict_row)
    return cur.execute(
        "select chapter_id, chapter_number from reading_progress"
        " where user_id = %s and manga_id = %s",
        (user_id, manga_id),
    ).fetchone()


@app.put("/api/me/progress/{manga_id}", status_code=204)
def save_progress(
    manga_id: str, p: ProgressIn, user_id: str = Depends(get_user_id), conn=Depends(get_conn)
):
    conn.execute(
        "insert into reading_progress (user_id, manga_id, chapter_id, chapter_number)"
        " values (%s, %s, %s, %s) on conflict (user_id, manga_id) do update"
        " set chapter_id = excluded.chapter_id, chapter_number = excluded.chapter_number,"
        " updated_at = now()",
        (user_id, manga_id, p.chapter_id, p.chapter_number),
    )
    conn.commit()


# ---------- importador / scraper (ZonaTMO e InManga) ----------


class ImportIn(BaseModel):
    url: str
    title: str | None = None
    type: str | None = None
    from_chapter: float | None = Field(default=None, ge=0)
    to_chapter: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _rango_valido(self) -> "ImportIn":
        if (
            self.from_chapter is not None
            and self.to_chapter is not None
            and self.from_chapter > self.to_chapter
        ):
            raise ValueError("from_chapter no puede ser mayor que to_chapter")
        return self


@app.get("/api/scraper/search")
async def scraper_search(
    q: str,
    source: Literal["zonatmo", "inmanga"] = "zonatmo",
    _user_id: str = Depends(get_user_id),
    scraper: ScraperClient = Depends(get_scraper),
):
    return {"items": await scraper.search(q, source)}


@app.post("/api/scraper/import")
async def scraper_import(
    body: ImportIn,
    _user_id: str = Depends(get_user_id),
    scraper: ScraperClient = Depends(get_scraper),
    catalog: LocalCatalog = Depends(get_catalog),
):
    try:
        return await scraper.import_manga(
            body.url,
            catalog,
            title_override=body.title,
            type_override=body.type,
            from_chapter=body.from_chapter,
            to_chapter=body.to_chapter,
        )
    except InvalidMangaUrl as e:
        raise HTTPException(400, "URL de manga no válida") from e
