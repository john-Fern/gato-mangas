import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { manga } from '../test/fixtures'
import { mockFetch, renderRoute } from '../test/utils'
import Home from './Home'

describe('Home', () => {
  it('muestra los mangas populares', async () => {
    mockFetch({ '/api/manga': { items: [manga], total: 1 } })
    renderRoute('/', '/', <Home />)
    expect(await screen.findByText('Solo Hero')).toBeInTheDocument()
    expect(screen.getByText('manhwa')).toBeInTheDocument()
  })

  it('busca por título', async () => {
    const fetchMock = mockFetch({ '/api/manga': { items: [], total: 0 } })
    renderRoute('/', '/', <Home />)
    await userEvent.type(screen.getByPlaceholderText(/buscar/i), 'solo{enter}')
    expect(await screen.findByText(/sin resultados/i)).toBeInTheDocument()
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain('q=solo')
  })
})
