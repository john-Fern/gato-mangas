import { supabase } from './supabase'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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

export type Page<T> = { items: T[]; total: number }
export type Favorite = { manga_id: string; title: string; cover_url: string | null }
export type Progress = { chapter_id: string; chapter_number: string | null }

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = (await supabase?.auth.getSession())?.data.session?.access_token
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!res.ok) throw new Error(`Error ${res.status}`)
  return res.status === 204 ? (undefined as T) : res.json()
}

export const imageUrl = (url: string | null) =>
  url ? `${API_URL}/api/image?url=${encodeURIComponent(url)}` : ''

export const api = {
  search: (q: string) =>
    request<Page<Manga>>(`/api/manga${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  manga: (id: string) => request<Manga>(`/api/manga/${id}`),
  chapters: (id: string, lang: string) =>
    request<Page<Chapter>>(`/api/manga/${id}/chapters?lang=${lang}&limit=500`),
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
}

export const chapterLabel = (c: Pick<Chapter, 'number' | 'title'>) =>
  `Cap. ${c.number ?? '?'}${c.title ? ` — ${c.title}` : ''}`
