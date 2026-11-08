import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Logo from '../Logo'
import { supabase } from '../supabase'

type Mode = 'login' | 'signup'
type Message = { kind: 'error' | 'ok'; text: string }

export default function Login() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('login')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<Message | null>(null)

  if (!supabase) return <p>El login no está configurado (faltan variables de Supabase).</p>
  const auth = supabase.auth

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const credentials = { email: String(form.get('email')), password: String(form.get('password')) }
    setBusy(true)
    setMessage(null)
    const { error } =
      mode === 'signup' ? await auth.signUp(credentials) : await auth.signInWithPassword(credentials)
    setBusy(false)
    if (error) return setMessage({ kind: 'error', text: error.message })
    if (mode === 'signup')
      return setMessage({ kind: 'ok', text: 'Cuenta creada. Revisa tu correo para confirmarla.' })
    navigate('/')
  }

  function switchTo(next: Mode) {
    setMode(next)
    setMessage(null)
  }

  const submitLabel = mode === 'login' ? 'Entrar' : 'Crear cuenta'

  return (
    <div className="auth">
      <form onSubmit={onSubmit} className="auth-card">
        <Logo size={56} />
        <h1>{mode === 'login' ? 'Bienvenido de vuelta' : 'Únete a Gato Mangas'}</h1>
        <p className="muted">Guarda tus favoritos y continúa donde lo dejaste.</p>

        <div className="tabs" role="tablist">
          {(['login', 'signup'] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => switchTo(m)}
            >
              {m === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}
            </button>
          ))}
        </div>

        <label className="field">
          Correo
          <input name="email" type="email" placeholder="tu@correo.com" autoComplete="email" required />
        </label>
        <label className="field">
          Contraseña
          <input
            name="password"
            type="password"
            placeholder="Mínimo 6 caracteres"
            minLength={6}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
          />
        </label>

        {message && (
          <p className={`notice ${message.kind}`} role={message.kind === 'error' ? 'alert' : 'status'}>
            {message.text}
          </p>
        )}

        <button className="primary" disabled={busy}>
          {busy ? 'Un momento…' : submitLabel}
        </button>
        <Link to="/" className="muted back">
          ← Volver a explorar
        </Link>
      </form>
    </div>
  )
}
