import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { manga } from '../test/fixtures'
import { mockFetch, mockIntersectionObserver, renderRoute, scrollToBottom } from '../test/utils'
import Home from './Home'

const lastUrl = (f: ReturnType<typeof vi.fn>) => String(f.mock.calls.at(-1)?.[0])
const genres = [{ id: 'g-action', name: 'Acción' }]
const mangaCalls = (f: ReturnType<typeof vi.fn>) =>
  f.mock.calls.filter((c) => String(c[0]).includes('/api/manga'))

describe('Home', () => {
  beforeEach(mockIntersectionObserver)

  it('muestra los mangas populares', async () => {
    mockFetch({ '/api/genres': genres, '/api/manga': { items: [manga], total: 1 } })
    renderRoute('/', '/', <Home />)
    expect(await screen.findByText('Solo Hero')).toBeInTheDocument()
    expect(screen.getByText('manhwa')).toBeInTheDocument()
  })

  it('busca por título', async () => {
    const fetchMock = mockFetch({ '/api/genres': genres, '/api/manga': { items: [], total: 0 } })
    renderRoute('/', '/', <Home />)
    await userEvent.type(screen.getByPlaceholderText(/buscar/i), 'solo{enter}')
    expect(await screen.findByText(/sin resultados/i)).toBeInTheDocument()
    expect(lastUrl(fetchMock)).toContain('q=solo')
  })

  it('filtra por tipo', async () => {
    const fetchMock = mockFetch({ '/api/genres': genres, '/api/manga': { items: [manga], total: 1 } })
    renderRoute('/', '/', <Home />)
    await screen.findByText('Solo Hero')
    await userEvent.click(screen.getByRole('button', { name: 'Manhwa' }))
    expect(lastUrl(fetchMock)).toContain('type=manhwa')
    expect(screen.getByRole('button', { name: 'Manhwa' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('carga la siguiente página al llegar al final', async () => {
    const second = { ...manga, id: 'm2', title: 'Segundo' }
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes('/api/genres')) return new Response(JSON.stringify(genres))
      const page = String(input).includes('offset=24') ? [second] : [manga]
      return new Response(JSON.stringify({ items: page, total: 30 }))
    })
    vi.stubGlobal('fetch', fetchMock)
    renderRoute('/', '/', <Home />)
    await screen.findByText('Solo Hero')

    await act(async () => scrollToBottom())

    expect(await screen.findByText('Segundo')).toBeInTheDocument()
    expect(screen.getByText('Solo Hero')).toBeInTheDocument()
    expect(lastUrl(fetchMock)).toContain('offset=24')
  })

  it('no pide más cuando ya cargó todo', async () => {
    const fetchMock = mockFetch({ '/api/genres': genres, '/api/manga': { items: [manga], total: 1 } })
    renderRoute('/', '/', <Home />)
    await screen.findByText('Solo Hero')
    await act(async () => scrollToBottom())
    expect(mangaCalls(fetchMock)).toHaveLength(1)
  })
  it('filtra por género, estado, demografía, orden e idioma', async () => {
    const fetchMock = mockFetch({ '/api/genres': genres, '/api/manga': { items: [manga], total: 1 } })
    renderRoute('/', '/', <Home />)
    await screen.findByText('Solo Hero')

    await userEvent.selectOptions(await screen.findByLabelText('Género'), 'Acción')
    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'Finalizado')
    await userEvent.selectOptions(screen.getByLabelText('Demografía'), 'Seinen')
    await userEvent.selectOptions(screen.getByLabelText('Ordenar por'), 'Últimas actualizaciones')
    await userEvent.click(screen.getByLabelText(/con capítulos en español/i))

    const url = lastUrl(fetchMock)
    for (const part of ['genre=g-action', 'status=completed', 'demographic=seinen', 'sort=latest', 'lang=es']) {
      expect(url).toContain(part)
    }
  })

  it('al cambiar un filtro vuelve a la primera página', async () => {
    const fetchMock = mockFetch({ '/api/genres': genres, '/api/manga': { items: [manga], total: 1 } })
    renderRoute('/', '/', <Home />)
    await screen.findByText('Solo Hero')
    await userEvent.selectOptions(screen.getByLabelText('Ordenar por'), 'Mejor valorados')
    expect(lastUrl(fetchMock)).toContain('offset=0')
  })
})
