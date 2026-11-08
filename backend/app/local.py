"""Mangas propios: los que guarda scraper-manga en las tablas `mangas` y `chapters`.

Se reconocen por el prefijo del id (zonatmo-…, inmanga-…) y se devuelven con la misma forma
que los de MangaDex, así el frontend no necesita saber de dónde vienen.
"""

import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from app.mangadex import NotFound

PREFIXES = ("zonatmo-", "inmanga-")
TYPES = ("manga", "manhwa", "manhua")
# dominio de las imágenes -> Referer que exige ese sitio
REFERERS = {
    "zonatmo.org": "https://zonatmo.org/",
    "inmanga.com": "https://inmanga.com/",
    "intomanga.com": "https://inmanga.com/",
}
GENERIC_TITLE = re.compile(r"^cap[ií]tulo\s+[\d.]+$", re.I)


def is_local(manga_or_chapter_id: str) -> bool:
    return manga_or_chapter_id.startswith(PREFIXES)


def image_referer(url: str) -> str | None:
    """Referer para una imagen de los sitios del scraper; None si el host no está permitido."""
    p = urlparse(url)
    host = p.hostname or ""
    if p.scheme != "https":
        return None
    for domain, referer in REFERERS.items():
        if host == domain or host.endswith("." + domain):
            return referer
    return None


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
