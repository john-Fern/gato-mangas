import { describe, expect, it } from 'vitest'
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
