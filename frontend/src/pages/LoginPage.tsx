import { type FormEvent, useState } from 'react'
import { Link } from 'react-router'

import { useAuth } from '../auth/context'
import { Alert, Button, Card, Field } from '../components/ui'
import { errorMessage, t } from '../i18n/en'

export function LoginPage() {
  const { client } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async (action: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await action() // o GuestRoute redireciona quando o estado do Auth muda
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    void run(() => client.signInWithEmail(email, password))
  }

  return (
    <Card title={t.login.title}>
      <p className="text-sm text-slate-600">{t.login.sharedLogin}</p>
      {error && <Alert kind="error">{error}</Alert>}
      <Button
        type="button"
        variant="secondary"
        disabled={busy}
        onClick={() => void run(() => client.signInWithGoogle())}
      >
        {t.login.google}
      </Button>
      <p className="text-center text-sm text-slate-500">{t.login.or}</p>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field
          id="email"
          label={t.login.email}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          id="password"
          label={t.login.password}
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" disabled={busy}>
          {t.login.submit}
        </Button>
      </form>
      <Link to="/reset-password" className="text-sm text-indigo-700 underline">
        {t.login.forgot}
      </Link>
      <p className="text-sm text-slate-600">
        {t.login.noAccount}{' '}
        <Link to="/signup" className="text-indigo-700 underline">
          {t.login.signUp}
        </Link>
      </p>
    </Card>
  )
}
