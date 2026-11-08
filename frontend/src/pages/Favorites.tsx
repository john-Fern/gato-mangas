import { useEffect, useState } from 'react'
import { api, type Favorite } from '../api'
import MangaCard from '../MangaCard'
import { useSession } from '../supabase'

export default function Favorites() {
  const session = useSession()
  const [items, setItems] = useState<Favorite[] | null>(null)

  useEffect(() => {
    if (session) api.favorites().then(setItems)
  }, [session])

  if (!session) return <p>Inicia sesión para ver tus favoritos.</p>
  return (
    <>
      <h2>Mis favoritos</h2>
      {items?.length === 0 && <p>Aún no tienes favoritos.</p>}
      <div className="grid">
        {items?.map((f) => <MangaCard key={f.manga_id} id={f.manga_id} {...f} />)}
      </div>
    </>
  )
}
