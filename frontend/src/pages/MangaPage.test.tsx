import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  it('muestra 100 capítulos por página con anterior y siguiente', async () => {
    const many = Array.from({ length: 250 }, (_, i) => ({
      id: `c${i + 1}`,
      number: String(i + 1),
      title: null,
      language: 'es',
      pages: 10,
      external_url: null,
    }))
    mockFetch({ '/chapters': { items: many, total: 250 }, '/api/manga/m1': manga })
    renderRoute('/manga/m1', '/manga/:id', <MangaPage />)

    const list = await screen.findByRole('list', { name: 'Capítulos' })
    const numbers = () => within(list).getAllByRole('link').map((a) => a.textContent)
    const prev = () => screen.getAllByRole('button', { name: /anterior/i })[0]
    const next = () => screen.getAllByRole('button', { name: /siguiente/i })[0]

    expect(numbers()).toHaveLength(100)
    expect(numbers()[0]).toBe('Cap. 1')
    expect(prev()).toBeDisabled()
    expect(screen.getAllByText('Página 1 de 3')[0]).toBeInTheDocument()

    await userEvent.click(next())
    expect(numbers()[0]).toBe('Cap. 101')
    await userEvent.click(next())
    expect(numbers()).toHaveLength(50)
    expect(next()).toBeDisabled()

    await userEvent.click(prev())
    expect(numbers()[0]).toBe('Cap. 101')
  })

  it('no muestra paginación con 100 capítulos o menos', async () => {
    mockFetch({ '/chapters': chapters, '/api/manga/m1': manga })
    renderRoute('/manga/m1', '/manga/:id', <MangaPage />)
    await screen.findByRole('list', { name: 'Capítulos' })
    expect(screen.queryByRole('button', { name: /siguiente/i })).not.toBeInTheDocument()
  })
})
