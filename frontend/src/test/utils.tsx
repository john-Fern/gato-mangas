import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import type { ReactElement } from 'react'

/** Simula fetch: cada clave es un fragmento de URL y su valor el JSON a devolver. */
export function mockFetch(routes: Record<string, unknown>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const key = Object.keys(routes).find((k) => url.includes(k))
    if (key === undefined) return new Response('not found', { status: 404 })
    return new Response(JSON.stringify(routes[key]), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export function renderRoute(path: string, pattern: string, element: ReactElement) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={pattern} element={element} />
      </Routes>
    </MemoryRouter>,
  )
}

/** IntersectionObserver falso: `scrollToBottom()` simula que el sentinela entra en pantalla. */
let observers: IntersectionObserverCallback[] = []
export function mockIntersectionObserver() {
  observers = []
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(cb: IntersectionObserverCallback) {
        observers.push(cb)
      }
      observe() {}
      disconnect() {}
    },
  )
}
export function scrollToBottom() {
  const entry = { isIntersecting: true } as IntersectionObserverEntry
  observers.at(-1)?.([entry], {} as IntersectionObserver)
}
