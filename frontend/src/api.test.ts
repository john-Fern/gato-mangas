import { describe, expect, it, vi } from 'vitest'
import { imageUrl } from './api'

describe('imageUrl', () => {
  it('pasa la imagen por el proxy del backend', () => {
    expect(imageUrl('https://uploads.mangadex.org/a b.jpg')).toBe(
      'http://localhost:8000/api/image?url=https%3A%2F%2Fuploads.mangadex.org%2Fa%20b.jpg',
    )
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
