import { type FormEvent, useState } from 'react'
import { Link } from 'react-router'

import { useAuth } from '../auth/context'
import { Alert, Button, Card, Field } from '../components/ui'
import { errorMessage, t } from '../i18n/pt-BR'

export function ResetPasswordPage() {
  const { client } = useAuth()
  const [email, setEmail] = useState('')
  const [state, setState] = useState<{ kind: 'error' | 'info'; text: string } | null>(null)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await client.sendPasswordReset(email)
      setState({ kind: 'info', text: t.reset.sent })
    } catch (e) {
      // Não revela se o e-mail tem conta: só erros de formato/rede aparecem.
      const code = (e as { code?: string }).code
      setState(
        code === 'auth/user-not-found'
          ? { kind: 'info', text: t.reset.sent }
          : { kind: 'error', text: errorMessage(e) },
      )
    }
  }

  return (
    <Card title={t.reset.title}>
      <p className="text-slate-700">{t.reset.body}</p>
      {state && <Alert kind={state.kind}>{state.text}</Alert>}
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
        <Field
          id="email"
          label={t.reset.email}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Button type="submit">{t.reset.submit}</Button>
      </form>
      <Link to="/login" className="text-sm text-indigo-700 underline">
        {t.reset.back}
      </Link>
    </Card>
  )
}
