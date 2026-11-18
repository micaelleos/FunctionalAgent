import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { t } from '../i18n/en'
import { fetchHealth, type Health } from '../lib/api'
import { SUPPORT_URL } from '../lib/links'

type ApiState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

/**
 * Página pública "Sobre": o fluxo do app e onde pedir ajuda (F12-RF-03), o link de privacidade
 * (F12-RF-04) e o status e a versão da API (F01-RF-03, F02-RF-03).
 */
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
    <main className="mx-auto flex max-w-xl flex-col gap-8 px-4 py-16">
      <header className="flex flex-col gap-3 text-center">
        <h1 className="text-2xl font-semibold">{t.app.name}</h1>
        <p className="text-slate-600">{t.about.body}</p>
      </header>

      <section aria-labelledby="about-how" className="flex flex-col gap-4">
        <h2 id="about-how" className="text-lg font-semibold">
          {t.about.howTitle}
        </h2>
        <ol className="flex flex-col gap-3">
          {t.about.steps.map((step, i) => (
            <li key={step.title} className="flex gap-3 rounded-lg border bg-white p-4">
              <span
                aria-hidden="true"
                className="flex size-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white"
              >
                {i + 1}
              </span>
              <div>
                <h3 className="font-medium">{step.title}</h3>
                <p className="text-sm text-slate-600">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="about-help" className="flex flex-col gap-2">
        <h2 id="about-help" className="text-lg font-semibold">
          {t.about.helpTitle}
        </h2>
        <p className="text-slate-600">{t.about.helpBody}</p>
        <p className="flex flex-wrap gap-x-6 gap-y-2">
          <a
            href={SUPPORT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-700 underline"
          >
            {t.about.helpLink}
          </a>
          <Link to="/privacy" className="text-indigo-700 underline">
            {t.about.privacyLink}
          </Link>
        </p>
      </section>

      <section
        aria-labelledby="about-status"
        aria-live="polite"
        className="flex flex-col gap-2 rounded-lg border bg-white px-4 py-3"
      >
        <h2 id="about-status" className="text-sm font-semibold text-slate-700">
          {t.about.statusTitle}
        </h2>
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
