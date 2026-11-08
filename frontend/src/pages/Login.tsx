import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../supabase'

export default function Login() {
  const navigate = useNavigate()
  const [message, setMessage] = useState('')

  if (!supabase) return <p>El login no está configurado (faltan variables de Supabase).</p>
  const auth = supabase.auth

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const submitter = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement
    const form = new FormData(e.currentTarget)
    const credentials = { email: String(form.get('email')), password: String(form.get('password')) }
    const { error } =
      submitter.value === 'signup'
        ? await auth.signUp(credentials)
        : await auth.signInWithPassword(credentials)
    if (error) return setMessage(error.message)
    if (submitter.value === 'signup') return setMessage('Revisa tu correo para confirmar la cuenta.')
    navigate('/')
  }

  return (
    <form onSubmit={onSubmit} className="login">
      <h2>Iniciar sesión</h2>
      <input name="email" type="email" placeholder="Correo" required />
      <input name="password" type="password" placeholder="Contraseña" minLength={6} required />
      <button value="login">Entrar</button>
      <button value="signup" className="secondary">
        Crear cuenta
      </button>
      {message && <p>{message}</p>}
    </form>
  )
}
