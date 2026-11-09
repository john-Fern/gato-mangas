import { Link } from 'react-router-dom'
import { imageUrl } from './api'

type Props = { id: string; title: string; cover_url: string | null; type?: string }

export default function MangaCard({ id, title, cover_url, type }: Props) {
  return (
    <Link to={`/manga/${id}`} className="card">
      {cover_url && <img src={imageUrl(cover_url)} alt="" loading="lazy" referrerPolicy="no-referrer" />}
      {type && <span className="badge">{type}</span>}
      <span className="card-title">{title}</span>
    </Link>
  )
}
