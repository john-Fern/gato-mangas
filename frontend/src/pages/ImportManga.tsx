import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type ImportResult, type ScraperCandidate, type ScraperSource } from '../api'
import { useSession } from '../supabase'

/** Convierte el texto del input en número de capítulo; vacío o inválido = sin límite. */
function parseChapter(value: string): number | undefined {
  if (value.trim() === '') return undefined
  const n = Number(value)
  return Number.isFinite(n) && n >= 0 ? n : undefined
}

export default function ImportManga() {
  const session = useSession()
  const [query, setQuery] = useState('')
  const [source, setSource] = useState<ScraperSource>('zonatmo')
  const [fromChapter, setFromChapter] = useState('')
  const [toChapter, setToChapter] = useState('')
  const [searching, setSearching] = useState(false)
  const [importingUrl, setImportingUrl] = useState<string | null>(null)
  const [results, setResults] = useState<ScraperCandidate[] | null>(null)
  const [imported, setImported] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!session) return <p>Inicia sesión para importar mangas al portal.</p>

  async function onSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    setSearching(true)
    setError(null)
    setImported(null)
    try {
      const res = await api.scraperSearch(q, source)
      setResults(res.items)
    } catch {
      setError('No se pudo buscar el manga. Verifica el nombre o enlace.')
    } finally {
      setSearching(false)
    }
  }

  async function onImport(item: ScraperCandidate) {
    const desde = parseChapter(fromChapter)
    const hasta = parseChapter(toChapter)
    if (desde !== undefined && hasta !== undefined && desde > hasta) {
      setError('El capítulo «desde» no puede ser mayor que «hasta».')
      return
    }
    setImportingUrl(item.url)
    setError(null)
    setImported(null)
    try {
      const res = await api.scraperImport({
        url: item.url,
        title: item.title,
        type: item.type,
        from_chapter: desde,
        to_chapter: hasta,
      })
      setImported(res)
    } catch {
      setError('Error al descargar y subir el manga al portal.')
    } finally {
      setImportingUrl(null)
    }
  }

  return (
    <section className="importer">
      <h2>Descargar y subir manga al portal</h2>
      <p className="muted">
        Ingresa el nombre o el link directo de una obra de ZonaTMO o InManga para descargar sus
        capítulos y publicarla en el catálogo de Gato Mangas.
      </p>

      <form onSubmit={onSearch} className="search-import">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Nombre o link del manga (ej. gachiakuta o https://zonatmo.org/...)"
          aria-label="Nombre o link del manga"
          required
        />
        <select
          value={source}
          onChange={(e) => setSource(e.target.value as ScraperSource)}
          aria-label="Fuente"
        >
          <option value="zonatmo">ZonaTMO</option>
          <option value="inmanga">InManga</option>
        </select>
        <input
          type="number"
          min={0}
          step="any"
          value={fromChapter}
          onChange={(e) => setFromChapter(e.target.value)}
          placeholder="Desde cap. (1º)"
          aria-label="Desde el capítulo"
          className="chapter-range"
        />
        <input
          type="number"
          min={0}
          step="any"
          value={toChapter}
          onChange={(e) => setToChapter(e.target.value)}
          placeholder="Hasta cap. (último)"
          aria-label="Hasta el capítulo"
          className="chapter-range"
        />
        <button disabled={searching || importingUrl !== null}>
          {searching ? 'Buscando…' : 'Buscar'}
        </button>
      </form>

      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}

      {imported && (
        <div className="notice ok" role="status">
          <p>
            <strong>{imported.title}</strong>: {imported.imported} capítulos nuevos subidos
            {imported.skipped > 0 ? ` (${imported.skipped} ya estaban en el portal)` : ''}
            {imported.failed > 0 ? `, ${imported.failed} no disponibles` : ''}.
          </p>
          <Link to={`/manga/${imported.manga_id}`} className="button">
            Ver en el portal →
          </Link>
        </div>
      )}

      {results?.length === 0 && <p>Sin resultados para «{query}».</p>}

      {results && results.length > 0 && (
        <ul className="import-list" aria-label="Resultados de búsqueda">
          {results.map((item) => {
            const busy = importingUrl === item.url
            return (
              <li key={`${item.source}-${item.id}`} className="import-item">
                <div>
                  <strong>{item.title}</strong>{' '}
                  <span className="badge">{item.type}</span>{' '}
                  <small className="muted">({item.source})</small>
                </div>
                <button
                  type="button"
                  disabled={importingUrl !== null}
                  onClick={() => onImport(item)}
                >
                  {busy ? 'Subiendo al portal…' : 'Subir al portal'}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
