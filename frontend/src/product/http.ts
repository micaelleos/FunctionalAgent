import { apiFetch, type TokenGetter } from '../lib/api'
import type { components } from '../lib/api-schema'
import type { JiraConnection, JiraConnectionInput, ProductApi } from './types'
import { unavailableProductApi } from './unavailable'

type ApiConnection = components['schemas']['JiraConnection']

const BASE = '/api/v1/jira/connections'

const fromApi = (c: ApiConnection): JiraConnection => ({
  id: c.id,
  site: c.site_url.replace(/^https:\/\//, ''),
  email: c.email,
  accountName: c.account_name,
  tokenLast4: c.token_hint,
  validatedAt: c.last_validated_at,
  status: c.status,
})

/**
 * Produção: o que já existe no backend vai para a API real; o resto continua em
 * `unavailableProductApi` (estados vazios, F08-RT-08) até a feature dele entrar.
 */
export function createHttpProductApi(getToken: TokenGetter): ProductApi {
  const json = async <T>(path: string, init?: RequestInit): Promise<T> =>
    (await (await apiFetch(path, getToken, init)).json()) as T
  const send = (method: string, body: unknown): RequestInit => ({
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  // MVP: uma conexão por usuário (F04); a API já devolve lista para o futuro.
  const current = async (): Promise<JiraConnection | null> => {
    const [first] = await json<ApiConnection[]>(BASE)
    return first ? fromApi(first) : null
  }

  return {
    ...unavailableProductApi,
    features: { ...unavailableProductApi.features, jira: true },
    getJiraConnection: current,
    connectJira: async ({ site, email, token }: JiraConnectionInput) => {
      const body = { site_url: site, email, api_token: token }
      const existing = await current()
      const saved = existing
        ? await json<ApiConnection>(`${BASE}/${existing.id}`, send('PUT', body))
        : await json<ApiConnection>(BASE, send('POST', body))
      return fromApi(saved)
    },
    disconnectJira: async () => {
      const existing = await current()
      if (existing) await apiFetch(`${BASE}/${existing.id}`, getToken, { method: 'DELETE' })
    },
    validateJira: async () => {
      const existing = await current()
      if (!existing)
        throw Object.assign(new Error('sem conexão'), { code: 'jira-connection-not-found' })
      return fromApi(
        await json<ApiConnection>(`${BASE}/${existing.id}/validate`, { method: 'POST' }),
      )
    },
  }
}
