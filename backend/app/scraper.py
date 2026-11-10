"""Scraper e importador de mangas desde ZonaTMO (zonatmo.org) e InManga (inmanga.com).

Porta la lógica de `scraper-manga` (`tmo_descargar.py` e `inmanga_descargar.py`) usando
`httpx.AsyncClient` para integrarse en FastAPI y guardar las obras en `LocalCatalog`.
"""

import json
import re
from typing import Literal
from urllib.parse import unquote, urljoin

import httpx
from bs4 import BeautifulSoup

from app.local import LocalCatalog

TMO_BASE = "https://zonatmo.org"
INMANGA_BASE = "https://inmanga.com"
AJAX = {"X-Requested-With": "XMLHttpRequest"}

RE_TMO_URL = re.compile(
    r"^https?://(?:www\.)?zonatmo\.(?:org|com)/library/([^/]+)/(\d+)/([^/?#]+)", re.I
)
RE_INMANGA_URL = re.compile(
    r"^https?://(?:www\.)?inmanga\.com/ver/manga/([^/]+)/([0-9a-f-]{36})", re.I
)
RE_INMANGA_HREF = re.compile(r"/ver/manga/([^/]+)/([0-9a-f-]{36})", re.I)
RE_NUM = re.compile(r"Cap[ií]tulo\s+([\d.]+)", re.I)
RE_VIEWER = re.compile(r"""https?://[^'"\s]+/viewer/[^'"\s<]+""")
RE_REDIR = re.compile(
    r"""(?:location\.(?:replace|assign)\s*\(|location(?:\.href)?\s*=|url=)\s*['"]?([^'"\s;)>]+)""",
    re.I,
)
RE_PU = re.compile(r"var pu = '([^']+)'")


class InvalidMangaUrl(ValueError):
    pass


def parse_manga_url(url: str) -> dict | None:
    """Si `url` es un enlace válido de ZonaTMO o InManga, devuelve sus datos normalizados."""
    text = url.strip()
    m_tmo = RE_TMO_URL.match(text)
    if m_tmo:
        tipo, id_, slug = m_tmo.groups()
        return {
            "id": id_,
            "source": "zonatmo",
            "slug": slug,
            "title": unquote(slug).replace("-", " "),
            "type": tipo.lower(),
            "url": f"{TMO_BASE}/library/{tipo}/{id_}/{slug}",
        }
    m_im = RE_INMANGA_URL.match(text)
    if m_im:
        slug, id_ = m_im.groups()
        return {
            "id": id_,
            "source": "inmanga",
            "slug": slug,
            "title": unquote(slug).replace("-", " "),
            "type": "manga",
            "url": f"{INMANGA_BASE}/ver/manga/{slug}/{id_}",
        }
    return None


def _datos_obra_tmo(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    titulo = soup.select_one("h1.element-title")
    img = soup.select_one("img.book-thumbnail[src]")
    sinopsis = soup.select_one("#manga-synopsis, p.element-description")
    return {
        "title": titulo.get_text(strip=True) if titulo else None,
        "cover_url": str(img["src"]) if img else None,
        "description": sinopsis.get_text(strip=True) if sinopsis else None,
    }


def _listar_capitulos_tmo(html: str, base: str) -> list[tuple[float | None, str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    caps: list[tuple[float | None, str, str]] = []
    for li in soup.select("li.upload-link"):
        h4 = li.select_one(".chapter-number") or li.find("h4")
        a = li.select_one('a[href*="/view_uploads/"]')
        if not (h4 and a):
            continue
        titulo = " ".join(h4.get_text(" ", strip=True).split())
        m = RE_NUM.search(titulo)
        caps.append((float(m.group(1)) if m else None, titulo, urljoin(base, str(a["href"]))))
    if not caps:
        a = soup.select_one('a[href*="/view_uploads/"]')
        if a:
            caps.append((1.0, "One shot", urljoin(base, str(a["href"]))))
    caps.reverse()
    return sorted(caps, key=lambda c: (c[0] is None, c[0] or 0))


def _imagenes_tmo(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    imgs = soup.select("img.viewer-img, img.viewer-image, img.reader-image") or soup.select(
        "#main-container img"
    )
    out: list[str] = []
    for i in imgs:
        src = str(i.get("data-src") or i.get("src") or "")
        if src.startswith("http"):
            out.append(src)
    return out


def _parsear_inmanga(html: str) -> list[dict]:
    obras: list[dict] = []
    for a in BeautifulSoup(html, "html.parser").select("a.manga-result[href]"):
        m = RE_INMANGA_HREF.search(str(a["href"]))
        if m:
            slug, id_ = m.group(1), m.group(2)
            h4 = a.find("h4")
            obras.append(
                {
                    "id": id_,
                    "source": "inmanga",
                    "title": h4.get_text(strip=True) if h4 else unquote(slug).replace("-", " "),
                    "type": "manga",
                    "url": f"{INMANGA_BASE}/ver/manga/{slug}/{id_}",
                }
            )
    return obras


def _public_item(obra: dict) -> dict:
    return {
        "id": str(obra["id"]),
        "source": obra["source"],
        "title": obra["title"],
        "type": obra["type"],
        "url": obra["url"],
    }


class ScraperClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def search(self, q: str, source: Literal["zonatmo", "inmanga"] = "zonatmo") -> list[dict]:
        direct = parse_manga_url(q)
        if direct:
            return [_public_item(direct)]
        if source == "inmanga":
            data = {
                "filter[generes][]": "-1",
                "filter[queryString]": q,
                "filter[skip]": "0",
                "filter[take]": "20",
                "filter[sortby]": "2",
                "filter[broadcastStatus]": "0",
                "filter[onlyFavorites]": "false",
                "d": "",
            }
            r = await self.http.post(
                f"{INMANGA_BASE}/manga/getMangasConsultResult",
                data=data,
                headers={**AJAX, "Referer": f"{INMANGA_BASE}/manga/consult"},
            )
            r.raise_for_status()
            return _parsear_inmanga(r.text)

        r = await self.http.get(f"{TMO_BASE}/api/search/suggest", params={"q": q})
        r.raise_for_status()
        return [
            {
                "id": str(o["id"]),
                "source": "zonatmo",
                "title": o["title"],
                "type": o["type"],
                "url": o["url"],
            }
            for o in r.json()
        ]

    async def import_manga(
        self,
        url: str,
        catalog: LocalCatalog,
        title_override: str | None = None,
        type_override: str | None = None,
        max_chapters: int | None = None,
    ) -> dict:
        obra = parse_manga_url(url)
        if not obra:
            raise InvalidMangaUrl(url)
        if title_override:
            obra["title"] = title_override
        if type_override:
            obra["type"] = type_override
        if obra["source"] == "inmanga":
            return await self._import_inmanga(obra, catalog, max_chapters)
        return await self._import_tmo(obra, catalog, max_chapters)

    async def _import_tmo(
        self, obra: dict, catalog: LocalCatalog, max_chapters: int | None
    ) -> dict:
        r = await self.http.get(obra["url"])
        r.raise_for_status()
        html = r.text
        datos = _datos_obra_tmo(html)
        caps = _listar_capitulos_tmo(html, TMO_BASE)
        manga_id = f"zonatmo-{obra['id']}"
        title = datos["title"] or obra["title"]
        catalog.save_manga(
            {
                "id": manga_id,
                "source": "zonatmo",
                "title": title,
                "type": obra["type"],
                "url": obra["url"],
                "cover_url": datos["cover_url"],
                "description": datos["description"],
            }
        )
        en_db = catalog.existing_chapters(manga_id)
        imported, skipped, failed = 0, 0, 0
        for idx, (num, cap_title, url_upload) in enumerate(caps[: max_chapters or None], 1):
            numero = float(num if num is not None else idx)
            if numero in en_db:
                skipped += 1
                continue
            try:
                url_visor, imgs = await self._resolver_imagenes_tmo(url_upload, obra["url"])
                if not imgs:
                    raise RuntimeError("el visor no tiene imágenes")
                catalog.save_chapter(
                    {
                        "manga_id": manga_id,
                        "number": numero,
                        "title": cap_title,
                        "source_url": url_visor,
                        "image_urls": imgs,
                    }
                )
                imported += 1
            except Exception:
                failed += 1
        return {
            "manga_id": manga_id,
            "title": title,
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
        }

    async def _resolver_imagenes_tmo(self, url_upload: str, referer: str) -> tuple[str, list[str]]:
        r = await self.http.get(url_upload, headers={"Referer": referer})
        r.raise_for_status()
        url, html = str(r.url), r.text
        imgs = _imagenes_tmo(html)
        if imgs:
            return url, imgs
        if "/viewer/" not in url:
            m = RE_VIEWER.search(html) or RE_REDIR.search(html)
            if not m:
                raise RuntimeError(f"No se encontró el visor desde {url_upload}")
            url = urljoin(url, m.group(m.lastindex or 0))
            html = ""
        if "/paginated" in url:
            url = re.sub(r"/paginated(/\d+)?$", "/cascade", url)
            html = ""
        if not html:
            r = await self.http.get(url, headers={"Referer": referer})
            r.raise_for_status()
            url, html = str(r.url), r.text
        return url, _imagenes_tmo(html)

    async def _import_inmanga(
        self, obra: dict, catalog: LocalCatalog, max_chapters: int | None
    ) -> dict:
        r = await self.http.get(
            f"{INMANGA_BASE}/chapter/getall",
            params={"mangaIdentification": obra["id"]},
            headers=AJAX,
        )
        r.raise_for_status()
        datos = json.loads(r.json()["data"])
        caps = sorted(datos["result"] or [], key=lambda c: c["Number"])
        manga_id = f"inmanga-{obra['id']}"
        catalog.save_manga(
            {
                "id": manga_id,
                "source": "inmanga",
                "title": obra["title"],
                "type": "manga",
                "url": obra["url"],
                "cover_url": None,
                "description": None,
            }
        )
        en_db = catalog.existing_chapters(manga_id)
        imported, skipped, failed = 0, 0, 0
        for cap in caps[: max_chapters or None]:
            numero = float(cap["Number"])
            if numero in en_db:
                skipped += 1
                continue
            try:
                url_cap, imgs = await self._listar_imagenes_inmanga(obra, cap)
                if not imgs or not await self._disponible_inmanga(imgs[0], url_cap):
                    failed += 1
                    continue
                catalog.save_chapter(
                    {
                        "manga_id": manga_id,
                        "number": numero,
                        "title": f"Capítulo {numero:g}",
                        "source_url": url_cap,
                        "image_urls": imgs,
                    }
                )
                imported += 1
            except Exception:
                failed += 1
        return {
            "manga_id": manga_id,
            "title": obra["title"],
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
        }

    async def _listar_imagenes_inmanga(self, obra: dict, cap: dict) -> tuple[str, list[str]]:
        url_cap = (
            f"{INMANGA_BASE}/ver/manga/{obra['slug']}/"
            f"{cap['FriendlyChapterNumberUrl']}/{cap['Identification']}"
        )
        r_cap = await self.http.get(url_cap)
        r_cap.raise_for_status()
        m = RE_PU.search(r_cap.text)
        if not m:
            raise RuntimeError("el visor no publica la plantilla de imágenes")
        r_ctrl = await self.http.get(
            f"{INMANGA_BASE}/chapter/chapterIndexControls",
            params={"identification": cap["Identification"].lower()},
            headers=AJAX,
        )
        r_ctrl.raise_for_status()
        paginas: dict[str, int] = {}
        for o in BeautifulSoup(r_ctrl.text, "html.parser").select("#PageList option[value]"):
            paginas.setdefault(str(o["value"]), int(o.get_text(strip=True) or 0))
        orden = sorted(paginas.items(), key=lambda p: p[1])
        imgs = [
            m.group(1).replace("identification", pid).replace("pageNumber", str(n))
            for pid, n in orden
        ]
        return url_cap, imgs

    async def _disponible_inmanga(self, url_img: str, referer: str) -> bool:
        r = await self.http.get(url_img, headers={"Referer": referer})
        return r.status_code == 200 and len(r.content) > 100
