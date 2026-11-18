import { useEffect } from 'react'
import { useRouteError } from 'react-router'

import { t } from '../i18n/en'
import { reportRenderError } from '../lib/errorReporting'

/** Tela de erro de qualquer rota: relata o erro (F11-RT-11) e oferece recarregar. */
export function RouteError() {
  const error = useRouteError()
  useEffect(() => reportRenderError(error), [error])
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-50 px-4 text-center">
      <h1 className="text-2xl font-semibold text-zinc-900">{t.routeError.title}</h1>
      <p className="max-w-md text-zinc-700">{t.routeError.body}</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="min-h-11 rounded-lg bg-indigo-600 px-4 font-medium text-white hover:bg-indigo-700"
      >
        {t.routeError.reload}
      </button>
    </main>
  )
}
