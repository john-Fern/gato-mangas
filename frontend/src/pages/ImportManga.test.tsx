import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockFetch, renderRoute } from '../test/utils'
import ImportManga from './ImportManga'

const sessionMock = vi.hoisted(() => ({ current: { user: { email: 'gato@mail.com' } } as unknown }))
vi.mock('../supabase', () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: { access_token: 'tok' } } }) } },
  useSession: () => sessionMock.current,
}))

describe('ImportManga', () => {
  beforeEach(() => {
    sessionMock.current = { user: { email: 'gato@mail.com' } }
  })

  it('pide iniciar sesión si no hay usuario autenticado', () => {
    sessionMock.current = null
    renderRoute('/import', '/import', <ImportManga />)
    expect(screen.getByText(/inicia sesión para importar/i)).toBeInTheDocument()
  })

  it('busca por nombre o link y permite subir el manga al portal', async () => {
    const fetchMock = mockFetch({
      '/api/scraper/search': {
        items: [
          {
            id: '1682',
            source: 'zonatmo',
            title: 'Gachiakuta',
            type: 'manga',
            url: 'https://zonatmo.org/library/manga/1682/gachiakuta',
          },
        ],
      },
      '/api/scraper/import': {
        manga_id: 'zonatmo-1682',
        title: 'Gachiakuta',
        imported: 12,
        skipped: 2,
        failed: 0,
      },
    })

    renderRoute('/import', '/import', <ImportManga />)

    await userEvent.type(screen.getByPlaceholderText(/nombre o link/i), 'gachiakuta')
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(await screen.findByText('Gachiakuta')).toBeInTheDocument()
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/api/scraper/search?q=gachiakuta&source=zonatmo')

    await userEvent.click(screen.getByRole('button', { name: 'Subir al portal' }))

    expect(await screen.findByText(/12 capítulos nuevos subidos/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /ver en el portal/i })).toHaveAttribute(
      'href',
      '/manga/zonatmo-1682',
    )
  })
})
