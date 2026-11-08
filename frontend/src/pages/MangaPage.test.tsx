import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { chapters, manga } from '../test/fixtures'
import { mockFetch, renderRoute } from '../test/utils'
import MangaPage from './MangaPage'

const chapterList = (n: number) =>
  Array.from({ length: n }, (_, i) => ({
    id: `c${i + 1}`,
    number: String(i + 1),
    title: null,
    language: 'es',
    pages: 10,
    external_url: null,
  }))

async function renderWith(n: number, unavailable = 0) {
  mockFetch({ '/chapters': { items: chapterList(n), total: n, unavailable }, '/api/manga/m1': manga })
  renderRoute('/manga/m1', '/manga/:id', <MangaPage />)
  const list = await screen.findByRole('list', { name: 'Capítulos' })
  return () => within(list).getAllByRole('link').map((a) => a.textContent)
}
const pageButtons = () =>
  [...screen.getAllByRole('navigation', { name: 'Páginas de capítulos' })[0].children].map(
    (el) => el.textContent,
  )

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
    const numbers = await renderWith(250)
    const prev = () => screen.getAllByRole('button', { name: /anterior/i })[0]
    const next = () => screen.getAllByRole('button', { name: /siguiente/i })[0]

    expect(numbers()).toHaveLength(100)
    expect(numbers()[0]).toBe('Cap. 1')
    expect(prev()).toBeDisabled()

    await userEvent.click(next())
    expect(numbers()[0]).toBe('Cap. 101')
    await userEvent.click(next())
    expect(numbers()).toHaveLength(50)
    expect(next()).toBeDisabled()

    await userEvent.click(prev())
    expect(numbers()[0]).toBe('Cap. 101')
  })

  it('permite saltar directo a una página', async () => {
    const numbers = await renderWith(250)
    expect(pageButtons()).toEqual(['← Anterior', '1', '2', '3', 'Siguiente →'])
    expect(screen.getAllByRole('button', { name: 'Página 1' })[0]).toHaveAttribute('aria-current', 'page')

    await userEvent.click(screen.getAllByRole('button', { name: 'Página 3' })[0])

    expect(numbers()[0]).toBe('Cap. 201')
    expect(screen.getAllByRole('button', { name: 'Página 3' })[0]).toHaveAttribute('aria-current', 'page')
  })

  it('con muchas páginas resume las del medio', async () => {
    await renderWith(1200)
    expect(pageButtons()).toEqual(['← Anterior', '1', '2', '…', '12', 'Siguiente →'])

    await userEvent.click(screen.getAllByRole('button', { name: 'Página 12' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: 'Página 11' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: 'Página 10' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: 'Página 9' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: 'Página 8' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: 'Página 7' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: 'Página 6' })[0])
    expect(pageButtons()).toEqual(['← Anterior', '1', '…', '5', '6', '7', '…', '12', 'Siguiente →'])
  })

  it('explica cuando MangaDex retiró capítulos', async () => {
    await renderWith(3, 1389)
    expect(screen.getByText(/mangadex retiró 1389/i)).toBeInTheDocument()
  })

  it('no muestra paginación con 100 capítulos o menos', async () => {
    mockFetch({ '/chapters': chapters, '/api/manga/m1': manga })
    renderRoute('/manga/m1', '/manga/:id', <MangaPage />)
    await screen.findByRole('list', { name: 'Capítulos' })
    expect(screen.queryByRole('button', { name: /siguiente/i })).not.toBeInTheDocument()
  })
})
