import { supabase } from './supabase'

// `||` y no `??`: en CI una variable no definida llega como string vacío
export const API_URL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const PAGE_SIZE = 24

export type Manga = {
  id: string
  title: string
  description: string | null
  cover_url: string | null
  type: 'manga' | 'manhwa' | 'manhua' | 'other'
  status: string | null
  year: number | null
  tags: string[]
}

export type Chapter = {
  id: string
  number: string | null
  title: string | null
  language: string
  pages: number
  external_url: string | null
}

export type Genre = { id: string; name: string }
export type Page<T> = { items: T[]; total: number }
export type Favorite = { manga_id: string; title: string; cover_url: string | null }
export type Progress = { chapter_id: string; chapter_number: string | null }
export type ScraperSource = 'zonatmo' | 'inmanga'
export type ScraperCandidate = {
  id: string
  source: ScraperSource
  title: string
  type: string
  url: string
}
export type ImportResult = {
  manga_id: string
  title: string
  imported: number
  skipped: number
  failed: number
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = (await supabase?.auth.getSession())?.data.session?.access_token
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!res.ok) throw new Error(`Error ${res.status}`)
  return res.status === 204 ? (undefined as T) : res.json()
}

const isMangaDex = (url: string) => {
  const host = new URL(url).hostname
  return host === 'uploads.mangadex.org' || host.endsWith('.mangadex.network')
}

/** MangaDex pasa por el proxy del backend; las de los mangas propios se cargan directo (sin Referer):
 *  zonatmo bloquea al servidor y rechaza Referers de otros sitios. */
export const imageUrl = (url: string | null) => {
  if (!url) return ''
  return isMangaDex(url) ? `${API_URL}/api/image?url=${encodeURIComponent(url)}` : url
}

export const api = {
  /** `filters` son los parámetros de la URL de la portada (q, type, genre, sort…). */
  search: (filters: URLSearchParams, offset = 0) => {
    const params = new URLSearchParams(filters)
    params.set('offset', String(offset))
    params.set('limit', String(PAGE_SIZE))
    return request<Page<Manga>>(`/api/manga?${params}`)
  },
  genres: () => request<Genre[]>('/api/genres'),
  manga: (id: string) => request<Manga>(`/api/manga/${id}`),
  chapters: (id: string, lang: string) =>
    request<Page<Chapter> & { unavailable: number }>(`/api/manga/${id}/chapters?lang=${lang}`),
  pages: (chapterId: string) => request<{ pages: string[] }>(`/api/chapters/${chapterId}/pages`),
  favorites: () => request<Favorite[]>('/api/me/favorites'),
  addFavorite: (m: Manga) =>
    request<void>(`/api/me/favorites/${m.id}`, {
      method: 'PUT',
      body: JSON.stringify({ title: m.title, cover_url: m.cover_url }),
    }),
  removeFavorite: (id: string) => request<void>(`/api/me/favorites/${id}`, { method: 'DELETE' }),
  progress: (id: string) => request<Progress | null>(`/api/me/progress/${id}`),
  saveProgress: (id: string, c: Chapter) =>
    request<void>(`/api/me/progress/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ chapter_id: c.id, chapter_number: c.number }),
    }),
  scraperSearch: (q: string, source: ScraperSource) => {
    const params = new URLSearchParams({ q, source })
    return request<{ items: ScraperCandidate[] }>(`/api/scraper/search?${params}`)
  },
  scraperImport: (body: { url: string; title?: string; type?: string; max_chapters?: number }) =>
    request<ImportResult>('/api/scraper/import', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}

export const chapterLabel = (c: Pick<Chapter, 'number' | 'title'>) =>
  `Cap. ${c.number ?? '?'}${c.title ? ` — ${c.title}` : ''}`
