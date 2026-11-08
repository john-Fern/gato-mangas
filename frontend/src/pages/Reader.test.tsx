import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { chapters } from '../test/fixtures'
import { mockFetch, renderRoute } from '../test/utils'
import Reader from './Reader'

describe('Reader', () => {
  it('muestra las páginas y enlaza al siguiente capítulo', async () => {
    mockFetch({
      '/api/chapters/c1/pages': { pages: ['https://x.mangadex.network/1.png'] },
      '/chapters': chapters,
    })
    renderRoute('/read/m1/c1?lang=es', '/read/:mangaId/:chapterId', <Reader />)
    expect(await screen.findByAltText('Página 1')).toBeInTheDocument()
    const next = await screen.findAllByRole('link', { name: /siguiente/i })
    expect(next[0]).toHaveAttribute('href', '/read/m1/c2?lang=es')
  })
})
