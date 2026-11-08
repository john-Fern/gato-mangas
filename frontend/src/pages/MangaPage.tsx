import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, chapterLabel, imageUrl, type Chapter, type Manga, type Progress } from '../api'
import { useSession } from '../supabase'

// "Español" incluye España y Latinoamérica (el backend junta ambos).
const LANGS: Record<string, string> = { es: 'Español', en: 'Inglés' }
const savedLang = () => {
  const lang = localStorage.getItem('lang') ?? 'es'
  return lang in LANGS ? lang : 'es'
}

export default function MangaPage() {
  const { id = '' } = useParams()
  const session = useSession()
  const [manga, setManga] = useState<Manga | null>(null)
  const [loaded, setLoaded] = useState<{ key: string; items: Chapter[] } | null>(null)
  const [lang, setLang] = useState(savedLang)
  const [favorite, setFavorite] = useState(false)
  const [progress, setProgress] = useState<Progress | null>(null)

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
        <h2>Capítulos</h2>
        <select value={lang} onChange={(e) => changeLang(e.target.value)} aria-label="Idioma">
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        {!chapters && <p>Cargando…</p>}
        {chapters?.length === 0 && <p>No hay capítulos en este idioma.</p>}
        <ul>
          {chapters?.map((c) => (
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
      </section>
    </article>
  )
}
