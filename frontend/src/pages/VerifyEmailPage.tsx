import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'

import { useAuth } from '../auth/context'
import { Alert, Button, Card } from '../components/ui'
import { errorMessage, t } from '../i18n/en'

export function VerifyEmailPage() {
  const { status, user, client, refresh } = useAuth()
  const navigate = useNavigate()
  const [message, setMessage] = useState<{ kind: 'error' | 'info'; text: string } | null>(null)

  if (status === 'signed-in') return <Navigate to="/chat" replace />
  if (status === 'signed-out') return <Navigate to="/login" replace />
  if (status === 'loading') return null

  const confirm = async () => {
    try {
      if (await refresh()) void navigate('/chat', { replace: true })
      else setMessage({ kind: 'error', text: t.verify.stillUnverified })
    } catch (e) {
      setMessage({ kind: 'error', text: errorMessage(e) })
    }
  }

  const resend = async () => {
    try {
      await client.resendVerification()
      setMessage({ kind: 'info', text: t.verify.resent })
    } catch (e) {
      setMessage({ kind: 'error', text: errorMessage(e) })
    }
  }

  return (
    <Card title={t.verify.title}>
      <p className="text-slate-700">{t.verify.body(user?.email ?? '')}</p>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <Button type="button" onClick={() => void confirm()}>
        {t.verify.done}
      </Button>
      <Button type="button" variant="secondary" onClick={() => void resend()}>
        {t.verify.resend}
      </Button>
      <button
        type="button"
        className="text-sm text-indigo-700 underline"
        onClick={() => void client.signOut()}
      >
        {t.verify.other}
      </button>
    </Card>
  )
}
