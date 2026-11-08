import { useEffect, useState } from 'react'
import { api, type Genre } from './api'

const TYPES = [
  ['', 'Todos'],
  ['manga', 'Manga'],
  ['manhwa', 'Manhwa'],
  ['manhua', 'Manhua'],
]
const STATUS = [
  ['', 'Cualquiera'],
  ['ongoing', 'En emisión'],
  ['completed', 'Finalizado'],
  ['hiatus', 'En pausa'],
  ['cancelled', 'Cancelado'],
]
const DEMOGRAPHICS = [
  ['', 'Cualquiera'],
  ['shounen', 'Shōnen'],
  ['shoujo', 'Shōjo'],
  ['seinen', 'Seinen'],
  ['josei', 'Josei'],
]
const SORTS = [
  ['latest', 'Últimas actualizaciones'],
  ['rating', 'Mejor valorados'],
  ['new', 'Más nuevos'],
  ['title', 'Título (A-Z)'],
]

type Props = { params: URLSearchParams; onChange: (key: string, value: string) => void }

function Select({ label, name, options, params, onChange }: Props & {
  label: string
  name: string
  options: string[][]
}) {
  return (
    <label>
      {label}
      <select value={params.get(name) ?? ''} onChange={(e) => onChange(name, e.target.value)}>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  )
}

export default function Filters({ params, onChange }: Props) {
  const [genres, setGenres] = useState<Genre[]>([])
  useEffect(() => {
    api.genres().then(setGenres, () => setGenres([]))
  }, [])

  const type = params.get('type') ?? ''
  const sorts = [['', params.get('q') ? 'Relevancia' : 'Popularidad'], ...SORTS]
  const genreOptions = [['', 'Todos'], ...genres.map((g) => [g.id, g.name])]
  const common = { params, onChange }

  return (
    <div className="filters">
      <div className="chips">
        {TYPES.map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={type === value}
            onClick={() => onChange('type', value)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="selects">
        <Select label="Género" name="genre" options={genreOptions} {...common} />
        <Select label="Estado" name="status" options={STATUS} {...common} />
        <Select label="Demografía" name="demographic" options={DEMOGRAPHICS} {...common} />
        <Select label="Ordenar por" name="sort" options={sorts} {...common} />
        <label className="check">
          <input
            type="checkbox"
            checked={params.get('lang') === 'es'}
            onChange={(e) => onChange('lang', e.target.checked ? 'es' : '')}
          />
          Con capítulos en español
        </label>
      </div>
    </div>
  )
}
