import { useEffect, useState } from 'react'

import { t } from '../i18n/en'
import { fetchHealth, type Health } from '../lib/api'

type ApiState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

/** Status e versão da API publicada, no rodapé da página inicial (F01-RF-03, F02-RF-03). */
export function ApiStatus() {
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
    <span aria-live="polite" className="text-xs">
      {api.kind === 'loading' && t.status.checking}
      {api.kind === 'ok' && (
        <>
          {t.status.ok} <span>{t.status.details(api.health.version, api.health.env)}</span>
        </>
      )}
      {api.kind === 'error' && (
        <span role="alert" className="text-red-700">
          {t.status.down} — {api.message}
        </span>
      )}
    </span>
  )
}
