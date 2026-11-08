import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type Manga } from '../api'
import MangaCard from '../MangaCard'

export default function Home() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const [result, setResult] = useState<{ q: string; items: Manga[] } | null>(null)
  const [error, setError] = useState('')
  const items = result?.q === q ? result.items : null

  useEffect(() => {
    api.search(q).then((r) => setResult({ q, items: r.items }), (e) => setError(String(e)))
  }, [q])

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const value = new FormData(e.currentTarget).get('q') as string
    setParams(value ? { q: value } : {})
  }

  return (
    <>
      <form onSubmit={onSubmit} className="search">
        <input name="q" defaultValue={q} placeholder="Buscar manga, manhwa, manhua…" />
        <button>Buscar</button>
      </form>
      <h2>{q ? `Resultados para “${q}”` : 'Populares'}</h2>
      {error && <p className="error">{error}</p>}
      {!items && !error && <p>Cargando…</p>}
      {items?.length === 0 && <p>Sin resultados.</p>}
      <div className="grid">
        {items?.map((m) => <MangaCard key={m.id} {...m} />)}
      </div>
    </>
  )
}
