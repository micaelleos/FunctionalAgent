import { useEffect, useState } from 'react'

import { fetchHealth, type Health } from './lib/api'

type ApiState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

export default function App() {
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
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 px-4 text-center">
      <img src="/logo.png" alt="" className="h-20 w-auto" />
      <h1 className="sr-only">Agente Funcional</h1>
      <p className="text-slate-600">
        Nova versão em construção. Acompanhe o plano em <code>docs/modernizacao</code>.
      </p>
      <section aria-live="polite" className="rounded-lg border px-4 py-3">
        {api.kind === 'loading' && <p>Verificando a API…</p>}
        {api.kind === 'ok' && (
          <p>
            <strong>API: ok</strong>{' '}
            <span className="text-slate-500">
              (versão {api.health.version}, ambiente {api.health.env})
            </span>
          </p>
        )}
        {api.kind === 'error' && (
          <p role="alert" className="text-red-700">
            <strong>API indisponível</strong> — {api.message}
          </p>
        )}
      </section>
    </main>
  )
}
