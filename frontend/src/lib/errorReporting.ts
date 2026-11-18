import { API_BASE_URL } from './api'

/**
 * Erros do SPA → `POST /api/v1/client-errors` → Error Reporting (F11-RT-11). Manda só a mensagem
 * do erro, a pilha e a rota; nada do que o usuário digitou. No máximo `MAX_REPORTS` por página.
 */
export const MAX_REPORTS = 5

export type ErrorKind = 'error' | 'unhandledrejection' | 'render'

export interface ClientErrorReport {
  message: string
  stack: string
  url: string
  release: string
  kind: ErrorKind
}

type Send = (report: ClientErrorReport) => void

const defaultSend: Send = (report) => {
  void fetch(`${API_BASE_URL}/api/v1/client-errors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report),
    keepalive: true, // chega mesmo se a página estiver fechando
  }).catch(() => {})
}

let reporter: ((kind: ErrorKind, error: unknown) => void) | null = null

function describe(error: unknown): { message: string; stack: string } {
  if (error instanceof Error) {
    return { message: `${error.name}: ${error.message}`, stack: error.stack ?? '' }
  }
  return { message: String(error), stack: '' }
}

export function installErrorReporting({
  release = import.meta.env.VITE_APP_VERSION ?? 'dev',
  send = defaultSend,
  target = window,
}: { release?: string; send?: Send; target?: Window } = {}): () => void {
  let sent = 0
  const report = (kind: ErrorKind, error: unknown) => {
    if (sent >= MAX_REPORTS) return
    sent += 1
    const { message, stack } = describe(error)
    send({
      message: message.slice(0, 500),
      stack: stack.slice(0, 6000),
      url: target.location.href,
      release: release.slice(0, 64),
      kind,
    })
  }
  const onError = (event: ErrorEvent) => report('error', event.error ?? event.message)
  const onRejection = (event: PromiseRejectionEvent) => report('unhandledrejection', event.reason)
  target.addEventListener('error', onError)
  target.addEventListener('unhandledrejection', onRejection)
  reporter = report
  return () => {
    target.removeEventListener('error', onError)
    target.removeEventListener('unhandledrejection', onRejection)
    reporter = null
  }
}

/** Erro de renderização pego pelo `errorElement` das rotas. */
export function reportRenderError(error: unknown): void {
  reporter?.('render', error)
}
