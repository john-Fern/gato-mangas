import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, chapterLabel, imageUrl, type Chapter, type Manga, type Progress } from '../api'
import { useSession } from '../supabase'

// "Español" incluye España y Latinoamérica (el backend junta ambos).
const LANGS: Record<string, string> = { es: 'Español', en: 'Inglés' }
const savedLang = () => {
  const lang = localStorage.getItem('lang') ?? 'es'
  return lang in LANGS ? lang : 'es'
}

const PER_PAGE = 100

function Pager({ page, pages, onChange }: { page: number; pages: number; onChange: (p: number) => void }) {
  if (pages <= 1) return null
  return (
    <div className="pager">
      <button disabled={page === 0} onClick={() => onChange(page - 1)}>
        ← Anterior
      </button>
      <span>
        Página {page + 1} de {pages}
      </span>
      <button disabled={page === pages - 1} onClick={() => onChange(page + 1)}>
        Siguiente →
      </button>
    </div>
  )
}

export default function MangaPage() {
  const { id = '' } = useParams()
  const session = useSession()
  const [manga, setManga] = useState<Manga | null>(null)
  const [loaded, setLoaded] = useState<{ key: string; items: Chapter[] } | null>(null)
  const [lang, setLang] = useState(savedLang)
  const [favorite, setFavorite] = useState(false)
  const [progress, setProgress] = useState<Progress | null>(null)
  // Página de capítulos; vuelve a la primera si cambia el manga o el idioma.
  const [paging, setPaging] = useState({ key: '', page: 0 })
  const listTop = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    api.manga(id).then(setManga)
  }, [id])

  useEffect(() => {
    api.chapters(id, lang).then((r) => setLoaded({ key: id + lang, items: r.items }))
  }, [id, lang])

  useEffect(() => {
    if (!session) return
    api.favorites().then((f) => setFavorite(f.some((x) => x.manga_id === id)))
    api.progress(id).then(setProgress)
  }, [id, session])

  async function toggleFavorite() {
    if (!manga) return
    await (favorite ? api.removeFavorite(id) : api.addFavorite(manga))
    setFavorite(!favorite)
  }

  function changeLang(value: string) {
    localStorage.setItem('lang', value)
    setLang(value)
  }

  const chapters = loaded?.key === id + lang ? loaded.items : null
  const page = paging.key === id + lang ? paging.page : 0
  const pages = Math.ceil((chapters?.length ?? 0) / PER_PAGE)
  const visible = chapters?.slice(page * PER_PAGE, (page + 1) * PER_PAGE)

  function goToPage(n: number) {
    setPaging({ key: id + lang, page: n })
    listTop.current?.scrollIntoView?.({ behavior: 'smooth' })
  }

  if (!manga) return <p>Cargando…</p>

  return (
    <article className="detail">
      {manga.cover_url && <img src={imageUrl(manga.cover_url)} alt="" className="cover" />}
      <div>
        <h1>{manga.title}</h1>
        <p className="meta">
          <span className="badge">{manga.type}</span> {manga.status} {manga.year}
        </p>
        <p>{manga.tags.join(' · ')}</p>
        <p className="description">{manga.description}</p>
        {session && (
          <button onClick={toggleFavorite}>{favorite ? '★ Quitar de favoritos' : '☆ Favorito'}</button>
        )}
        {progress && (
          <Link className="button" to={`/read/${id}/${progress.chapter_id}?lang=${lang}`}>
            Continuar: cap. {progress.chapter_number}
          </Link>
        )}
      </div>

      <section className="chapters">
        <h2 ref={listTop}>
          Capítulos {chapters && chapters.length > 0 && <small>({chapters.length})</small>}
        </h2>
        <select value={lang} onChange={(e) => changeLang(e.target.value)} aria-label="Idioma">
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        {!chapters && <p>Cargando…</p>}
        {chapters?.length === 0 && <p>No hay capítulos en este idioma.</p>}
        <Pager page={page} pages={pages} onChange={goToPage} />
        <ul aria-label="Capítulos">
          {visible?.map((c) => (
            <li key={c.id}>
              {c.external_url ? (
                <a href={c.external_url} target="_blank" rel="noreferrer">
                  {chapterLabel(c)} ↗
                </a>
              ) : (
                <Link to={`/read/${id}/${c.id}?lang=${lang}`}>{chapterLabel(c)}</Link>
              )}
            </li>
          ))}
        </ul>
        <Pager page={page} pages={pages} onChange={goToPage} />
      </section>
    </article>
  )
}
