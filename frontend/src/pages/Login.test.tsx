import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderRoute } from '../test/utils'
import Login from './Login'

const auth = vi.hoisted(() => ({
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
}))
vi.mock('../supabase', () => ({ supabase: { auth }, useSession: () => null }))

async function fill() {
  await userEvent.type(screen.getByLabelText('Correo'), 'gato@mail.com')
  await userEvent.type(screen.getByLabelText('Contraseña'), 'secreto123')
}

describe('Login', () => {
  beforeEach(() => vi.clearAllMocks())

  it('inicia sesión con correo y contraseña', async () => {
    auth.signInWithPassword.mockResolvedValue({ error: null })
    renderRoute('/login', '/login', <Login />)
    await fill()
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'gato@mail.com',
      password: 'secreto123',
    })
  })

  it('muestra el error de Supabase', async () => {
    auth.signInWithPassword.mockResolvedValue({ error: { message: 'Invalid login credentials' } })
    renderRoute('/login', '/login', <Login />)
    await fill()
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid login credentials')
  })

  it('permite cambiar a crear cuenta', async () => {
    auth.signUp.mockResolvedValue({ error: null })
    renderRoute('/login', '/login', <Login />)
    await userEvent.click(screen.getByRole('tab', { name: 'Crear cuenta' }))
    await fill()
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))
    expect(auth.signUp).toHaveBeenCalled()
    expect(await screen.findByRole('status')).toHaveTextContent(/revisa tu correo/i)
  })
})
