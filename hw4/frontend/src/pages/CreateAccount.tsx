import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, type SignupInput } from '../auth'

const MIN_PASSWORD_LENGTH = 8

export default function CreateAccount() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupInput>({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const update = (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const mismatch = form.confirm_password !== '' && form.password !== form.confirm_password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (form.password !== form.confirm_password) {
      setError("Passwords don't match.")
      return
    }
    setBusy(true)
    try {
      await signup(form)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section auth">
      <h1>Create account</h1>
      <p className="auth-sub">New player? Make an account to save your chat with our assistant.</p>
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="row">
          <label>
            First name
            <input name="first_name" autoComplete="given-name" value={form.first_name} onChange={update} required />
          </label>
          <label>
            Last name
            <input name="last_name" autoComplete="family-name" value={form.last_name} onChange={update} required />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" value={form.email} onChange={update} required />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            value={form.password}
            onChange={update}
            required
          />
          <small className="muted">At least {MIN_PASSWORD_LENGTH} characters.</small>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm_password"
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={update}
            required
          />
          {mismatch && <small className="error">Passwords don't match.</small>}
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
