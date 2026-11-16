import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import { API_BASE_URL } from '../lib/api'

export const PROFILE = {
  uid: 'uid-alice',
  display_name: 'Alice',
  email: 'alice@teste.dev',
  created_at: '2026-11-14T12:00:00Z',
  locale: 'pt-BR',
}

export const api = (path: string) => `${API_BASE_URL}${path}`

export const server = setupServer(
  http.get(api('/health'), () =>
    HttpResponse.json({ status: 'ok', version: 'abc123', env: 'local' }),
  ),
  http.get(api('/api/v1/me'), () => HttpResponse.json(PROFILE)),
  http.get(api('/api/v1/me/export'), () => HttpResponse.json({ uid: 'uid-alice', user: {} })),
  http.delete(api('/api/v1/me'), () => new HttpResponse(null, { status: 204 })),
  http.get(api('/api/v1/jira/connections'), () => HttpResponse.json([])),
)
