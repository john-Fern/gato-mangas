import '@testing-library/jest-dom/vitest'
window.scrollTo = () => {}
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
