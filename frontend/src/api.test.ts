import { describe, expect, it, vi } from 'vitest'
import { imageUrl } from './api'

describe('imageUrl', () => {
  it('pasa la imagen por el proxy del backend', () => {
    expect(imageUrl('https://uploads.mangadex.org/a b.jpg')).toBe(
      'http://localhost:8000/api/image?url=https%3A%2F%2Fuploads.mangadex.org%2Fa%20b.jpg',
    )
  })

  it('también pasa por el proxy las páginas de los servidores de MangaDex', () => {
    expect(imageUrl('https://x.mangadex.network/1.png')).toContain('/api/image?url=')
  })

  it('carga directo las imágenes de los mangas propios (el sitio bloquea al servidor)', () => {
    const zonatmo = 'https://storage2.zonatmo.org/chapters/1/a.webp'
    const inmanga = 'https://cdn1.intomanga.com/i/m/x.jpg'
    expect(imageUrl(zonatmo)).toBe(zonatmo)
    expect(imageUrl(inmanga)).toBe(inmanga)
  })

  it('devuelve vacío si no hay imagen', () => {
    expect(imageUrl(null)).toBe('')
  })
})

describe('API_URL', () => {
  it('usa localhost si VITE_API_URL viene vacía (CI sin variable)', async () => {
    vi.stubEnv('VITE_API_URL', '')
    vi.resetModules()
    const { API_URL } = await import('./api')
    expect(API_URL).toBe('http://localhost:8000')
    vi.unstubAllEnvs()
  })
})
