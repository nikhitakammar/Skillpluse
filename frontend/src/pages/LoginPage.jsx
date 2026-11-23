import { useState } from 'react'
import '../styles/auth.css'

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try { await onLogin(username, password) }
    catch (reason) { setError(reason.message || 'Sign-in failed. Check your username and password.') }
    finally { setLoading(false) }
  }

  return (
    <main className="auth-screen">
      <section className="auth-card">
        <div className="auth-brand"><span className="brand-mark">S</span><span>Skill Pluse</span></div>
        <span className="eyebrow">SECURE WORKSPACE</span>
        <h1>Welcome back</h1>
        <p>Sign in with the account provided by your Skill Pluse administrator.</p>
        <form onSubmit={submit}>
          <label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required minLength="3" maxLength="40" /></label>
          <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required maxLength="128" /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="primary-button auth-submit" type="submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <p className="auth-demo-note">Use synthetic demonstration data only. Support signals are for trainer review.</p>
      </section>
    </main>
  )
}

export default LoginPage
