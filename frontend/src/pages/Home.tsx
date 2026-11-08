import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, PAGE_SIZE, type Manga } from '../api'
import MangaCard from '../MangaCard'

const TYPES = [
  ['', 'Todos'],
  ['manga', 'Manga'],
  ['manhwa', 'Manhwa'],
  ['manhua', 'Manhua'],
] as const

type Loaded = { key: string; page: number; items: Manga[]; total: number }

export default function Home() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const type = params.get('type') ?? ''
  const key = `${q}|${type}`

  // Página pedida (por búsqueda/filtro) y lo ya cargado; si cambia el filtro se vuelve a la 0.
  const [wanted, setWanted] = useState({ key, page: 0 })
  const page = wanted.key === key ? wanted.page : 0
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [error, setError] = useState('')
  const current = loaded?.key === key ? loaded : null
  const loading = current?.page !== page
  const hasMore = !!current && current.items.length < current.total
  const sentinel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let stale = false
    api.search(q, type, page * PAGE_SIZE).then(
      (r) => {
        if (stale) return
        setLoaded((prev) => {
          const before = page > 0 && prev?.key === key ? prev.items : []
          const ids = new Set(before.map((m) => m.id))
          const items = [...before, ...r.items.filter((m) => !ids.has(m.id))]
          return { key, page, items, total: r.total }
        })
      },
      (e) => !stale && setError(String(e)),
    )
    return () => {
      stale = true
    }
  }, [q, type, key, page])

  useEffect(() => {
    if (loading || !hasMore || !sentinel.current) return
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setWanted({ key, page: page + 1 }),
      { rootMargin: '800px' },
    )
    observer.observe(sentinel.current)
    return () => observer.disconnect()
  }, [loading, hasMore, key, page])

  function update(next: { q?: string; type?: string }) {
    const merged = { q, type, ...next }
    setParams(Object.fromEntries(Object.entries(merged).filter(([, v]) => v)))
  }

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    update({ q: new FormData(e.currentTarget).get('q') as string })
  }

  return (
    <>
      <form onSubmit={onSubmit} className="search">
        <input name="q" defaultValue={q} placeholder="Buscar manga, manhwa, manhua…" />
        <button>Buscar</button>
      </form>
      <div className="filters">
        {TYPES.map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={type === value}
            onClick={() => update({ type: value })}
          >
            {label}
          </button>
        ))}
      </div>
      <h2>{q ? `Resultados para “${q}”` : 'Populares'}</h2>
      {error && <p className="error">{error}</p>}
      {current?.items.length === 0 && <p>Sin resultados.</p>}
      <div className="grid">
        {current?.items.map((m) => <MangaCard key={m.id} {...m} />)}
      </div>
      {loading && !error && <p className="loading">Cargando…</p>}
      <div ref={sentinel} />
    </>
  )
}
