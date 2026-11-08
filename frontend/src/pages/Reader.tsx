import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, chapterLabel, imageUrl, type Chapter } from '../api'
import { useSession } from '../supabase'

export default function Reader() {
  const { mangaId = '', chapterId = '' } = useParams()
  const lang = useSearchParams()[0].get('lang') ?? 'es'
  const session = useSession()
  const [loaded, setLoaded] = useState<{ id: string; pages: string[] } | null>(null)
  const pages = loaded?.id === chapterId ? loaded.pages : null
  const [chapters, setChapters] = useState<Chapter[]>([])

  useEffect(() => {
    api.pages(chapterId).then((r) => {
      setLoaded({ id: chapterId, pages: r.pages })
      window.scrollTo(0, 0)
    })
  }, [chapterId])

  useEffect(() => {
    api.chapters(mangaId, lang).then((r) => setChapters(r.items))
  }, [mangaId, lang])

  const index = chapters.findIndex((c) => c.id === chapterId)
  const current = chapters[index]

  useEffect(() => {
    if (session && current) api.saveProgress(mangaId, current)
  }, [session, current, mangaId])

  const link = (c?: Chapter) => c && `/read/${mangaId}/${c.id}?lang=${lang}`
  const nav = (
    <nav className="reader-nav">
      {index > 0 && <Link to={link(chapters[index - 1])!}>← Anterior</Link>}
      <Link to={`/manga/${mangaId}`}>{current ? chapterLabel(current) : 'Volver'}</Link>
      {index >= 0 && index < chapters.length - 1 && (
        <Link to={link(chapters[index + 1])!}>Siguiente →</Link>
      )}
    </nav>
  )

  return (
    <div className="reader">
      {nav}
      {!pages && <p>Cargando…</p>}
      {pages?.map((p, i) => (
        <img key={p} src={imageUrl(p)} alt={`Página ${i + 1}`} loading="lazy" />
      ))}
      {nav}
    </div>
  )
}
