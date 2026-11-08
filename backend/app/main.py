import os
from collections.abc import AsyncIterator, Iterator
from urllib.parse import urlparse

import httpx
import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel

from app.mangadex import MangaDexClient, NotFound

app = FastAPI(title="Gato Mangas API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_AGENT = "gato-mangas/0.1"
_http = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT})


# ---------- dependencias ----------


async def get_mangadex() -> AsyncIterator[MangaDexClient]:
    yield MangaDexClient(_http)


def get_conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        yield conn


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


@app.get("/api/manga")
async def search(
    q: str | None = None,
    limit: int = Query(24, le=100),
    offset: int = 0,
    md: MangaDexClient = Depends(get_mangadex),
):
    return await md.search(q, limit, offset)


@app.get("/api/manga/{manga_id}")
async def manga(manga_id: str, md: MangaDexClient = Depends(get_mangadex)):
    return await md.manga(manga_id)


@app.get("/api/manga/{manga_id}/chapters")
async def chapters(
    manga_id: str,
    lang: str = "es",
    limit: int = Query(100, le=500),
    offset: int = 0,
    md: MangaDexClient = Depends(get_mangadex),
):
    return await md.chapters(manga_id, lang, limit, offset)


@app.get("/api/chapters/{chapter_id}/pages")
async def pages(chapter_id: str, md: MangaDexClient = Depends(get_mangadex)):
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
