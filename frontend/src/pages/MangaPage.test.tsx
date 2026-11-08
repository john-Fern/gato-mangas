import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { chapters, manga } from '../test/fixtures'
import { mockFetch, renderRoute } from '../test/utils'
import MangaPage from './MangaPage'

describe('MangaPage', () => {
  it('muestra detalle y capítulos', async () => {
    mockFetch({ '/chapters': chapters, '/api/manga/m1': manga })
    renderRoute('/manga/m1', '/manga/:id', <MangaPage />)
    expect(await screen.findByRole('heading', { name: 'Solo Hero' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /cap\. 1 — inicio/i })).toHaveAttribute(
      'href',
      '/read/m1/c1?lang=es',
    )
  })
  it('usa español si había guardado un idioma que ya no existe', async () => {
    localStorage.setItem('lang', 'es-la')
    const fetchMock = mockFetch({ '/chapters': chapters, '/api/manga/m1': manga })
    renderRoute('/manga/m1', '/manga/:id', <MangaPage />)
    await screen.findByRole('heading', { name: 'Solo Hero' })
    expect(fetchMock.mock.calls.some((c) => String(c[0]).includes('chapters?lang=es'))).toBe(true)
    expect(screen.getByLabelText('Idioma')).toHaveValue('es')
  })
})
