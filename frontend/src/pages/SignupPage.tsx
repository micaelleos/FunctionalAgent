import { type FormEvent, useState } from 'react'
import { Link } from 'react-router'

import { useAuth } from '../auth/context'
import { Alert, Button, Card, Field } from '../components/ui'
import { errorMessage, t } from '../i18n/pt-BR'

export function SignupPage() {
  const { client } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      // Depois do cadastro, o GuestRoute leva para /verificar-email (conta ainda não confirmada).
      await client.signUp(name.trim(), email, password)
    } catch (e) {
      setError(errorMessage(e))
      setBusy(false)
    }
  }

  return (
    <Card title={t.signup.title}>
      {error && <Alert kind="error">{error}</Alert>}
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
        <Field
          id="name"
          label={t.signup.name}
          autoComplete="name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Field
          id="email"
          label={t.signup.email}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          id="password"
          label={t.signup.password}
          type="password"
          autoComplete="new-password"
          minLength={6}
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" disabled={busy}>
          {t.signup.submit}
        </Button>
      </form>
      <p className="text-sm text-slate-600">
        {t.signup.hasAccount}{' '}
        <Link to="/login" className="text-sky-800 underline">
          {t.signup.signIn}
        </Link>
      </p>
    </Card>
  )
}
