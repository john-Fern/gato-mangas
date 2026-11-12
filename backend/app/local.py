"""Mangas propios: los que guarda scraper-manga en las tablas `mangas` y `chapters`.

Se reconocen por el prefijo del id (zonatmo-…, inmanga-…) y se devuelven con la misma forma
que los de MangaDex, así el frontend no necesita saber de dónde vienen.
Sus imágenes no pasan por el proxy: zonatmo bloquea al servidor, el navegador las carga directo.
"""

import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.rows import dict_row

from app.mangadex import NotFound

PREFIXES = ("zonatmo-", "inmanga-")
TYPES = ("manga", "manhwa", "manhua")
GENERIC_TITLE = re.compile(r"^cap[ií]tulo\s+[\d.]+$", re.I)


def is_local(manga_or_chapter_id: str) -> bool:
    return manga_or_chapter_id.startswith(PREFIXES)


def _number(n: Decimal) -> str:
    return f"{n.normalize():f}"  # 2.0 -> "2", 1.50 -> "1.5"


def _manga(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "cover_url": row["cover_url"],
        "type": row["type"] if row["type"] in TYPES else "other",
        "status": None,
        "year": None,
        "tags": [],
    }


class LocalCatalog:
    def __init__(self, connect: Callable[[], psycopg.Connection]):
        self.connect = connect  # se conecta solo si se usa

    def _rows(self, sql: str, params) -> list[dict]:
        with self.connect() as conn:
            return conn.cursor(row_factory=dict_row).execute(sql, params).fetchall()

    def search(self, q: str | None, type: str | None) -> list[dict]:
        rows = self._rows(
            "select * from mangas"
            " where (%(q)s::text is null or title ilike '%%' || %(q)s || '%%')"
            " and (%(type)s::text is null or type = %(type)s)"
            " order by title",
            {"q": q, "type": type},
        )
        return [_manga(r) for r in rows]

    def manga(self, manga_id: str) -> dict:
        rows = self._rows("select * from mangas where id = %s", (manga_id,))
        if not rows:
            raise NotFound(manga_id)
        return _manga(rows[0])

    def chapters(self, manga_id: str) -> dict:
        self.manga(manga_id)
        rows = self._rows(
            "select number, title, cardinality(image_urls) as pages from chapters"
            " where manga_id = %s order by number",
            (manga_id,),
        )
        items = [
            {
                "id": f"{manga_id}~{_number(r['number'])}",
                "number": _number(r["number"]),
                "title": None if GENERIC_TITLE.match(r["title"] or "") else r["title"],
                "language": "es",
                "pages": r["pages"],
                "external_url": None,
            }
            for r in rows
        ]
        return {"items": items, "total": len(items), "unavailable": 0}

    def pages(self, chapter_id: str) -> list[str]:
        manga_id, _, number = chapter_id.rpartition("~")
        try:
            Decimal(number)
        except InvalidOperation:
            raise NotFound(chapter_id) from None
        rows = self._rows(
            "select image_urls from chapters where manga_id = %s and number = %s::numeric",
            (manga_id, number),
        )
        if not rows:
            raise NotFound(chapter_id)
        return rows[0]["image_urls"]

    def existing_chapters(self, manga_id: str) -> set[float]:
        rows = self._rows("select number from chapters where manga_id = %s", (manga_id,))
        return {float(r["number"]) for r in rows}

    def save_manga(self, manga: dict) -> None:
        """Crea o actualiza la obra. Portada y descripción solo se rellenan si faltan:
        nunca se pisan las que ya existen ni se borran con un valor vacío."""
        with self.connect() as conn:
            conn.execute(
                "insert into mangas (id, source, title, type, url, cover_url, description)"
                " values (%(id)s, %(source)s, %(title)s, %(type)s, %(url)s,"
                " nullif(%(cover_url)s, ''), nullif(%(description)s, ''))"
                " on conflict (id) do update set"
                " title = excluded.title, type = excluded.type, url = excluded.url,"
                " cover_url = coalesce(nullif(mangas.cover_url, ''), excluded.cover_url),"
                " description = coalesce(nullif(mangas.description, ''), excluded.description)",
                {"cover_url": None, "description": None, **manga},
            )
            conn.commit()

    def save_chapter(self, chapter: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into chapters (manga_id, number, title, source_url, image_urls)"
                " values (%(manga_id)s, %(number)s, %(title)s, %(source_url)s, %(image_urls)s)"
                " on conflict (manga_id, number) do update set"
                " title = excluded.title, source_url = excluded.source_url,"
                " image_urls = excluded.image_urls",
                chapter,
            )
            conn.commit()
