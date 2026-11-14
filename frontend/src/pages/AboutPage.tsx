import { useEffect, useState } from 'react'

import { t } from '../i18n/pt-BR'
import { fetchHealth, type Health } from '../lib/api'

type ApiState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

/** Página pública "Sobre", com o status e a versão da API (F01-RF-03, F02-RF-03). */
export function AboutPage() {
  const [api, setApi] = useState<ApiState>({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
      .then((health) => setApi({ kind: 'ok', health }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setApi({ kind: 'error', message: error instanceof Error ? error.message : String(error) })
      })
    return () => controller.abort()
  }, [])

  return (
    <main className="mx-auto flex max-w-xl flex-col items-center gap-6 px-4 py-16 text-center">
      <h1 className="text-2xl font-semibold">{t.app.name}</h1>
      <p className="text-slate-600">
        Agente que ajuda Product Owners a escrever épicos, user stories em BDD e tarefas, e a
        exportá-los para o Jira.
      </p>
      <section aria-live="polite" className="rounded-lg border bg-white px-4 py-3">
        {api.kind === 'loading' && <p>{t.status.checking}</p>}
        {api.kind === 'ok' && (
          <p>
            <strong>{t.status.ok}</strong>{' '}
            <span className="text-slate-500">
              {t.status.details(api.health.version, api.health.env)}
            </span>
          </p>
        )}
        {api.kind === 'error' && (
          <p role="alert" className="text-red-700">
            <strong>{t.status.down}</strong> — {api.message}
          </p>
        )}
      </section>
    </main>
  )
}
