import { apiFetch, type TokenGetter } from '../lib/api'
import type { components } from '../lib/api-schema'
import { streamPost } from '../lib/sse'
import type {
  ChatMessage,
  ConversationSummary,
  JiraConnection,
  JiraConnectionInput,
  JiraProject,
  ProductApi,
} from './types'
import { type ApiAction, fromApiAction, toActionProblem } from './actions'
import { unavailableProductApi } from './unavailable'

type ApiConnection = components['schemas']['JiraConnection']
type ApiConversation = components['schemas']['ConversationOut']
type ApiConversationPage = components['schemas']['ConversationPage']
type ApiMessagePage = components['schemas']['MessagePage']
type ApiMessage = components['schemas']['MessageOut']
type ApiProjectList = components['schemas']['JiraProjectList']

const BASE = '/api/v1/jira/connections'
const CONVERSATIONS = '/api/v1/conversations'
/** A lateral mostra as conversas mais recentes (F08-RF-05); paginar a lista fica para depois. */
const SIDEBAR_LIMIT = 50

/** `VITE_FEATURE_CHAT=false` no build desliga o envio (rollback da F08). */
const CHAT_ENABLED = import.meta.env.VITE_FEATURE_CHAT !== 'false'

const conversationFromApi = (c: ApiConversation): ConversationSummary => ({
  id: c.id,
  title: c.title,
  projectKey: c.project_key ?? null,
  updatedAt: c.updated_at,
})

const messageFromApi = (m: ApiMessage): ChatMessage => ({
  id: m.id,
  role: m.role,
  text: m.text,
  actions: m.actions.map(fromApiAction),
  interrupted: m.interrupted ?? false,
})

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

  const decide = async (id: string, verb: 'confirm' | 'reject') => {
    try {
      return fromApiAction(
        await json<ApiAction>(`/api/v1/actions/${encodeURIComponent(id)}/${verb}`, {
          method: 'POST',
        }),
      )
    } catch (error) {
      throw toActionProblem(error)
    }
  }

  // MVP: uma conexão por usuário (F04); a API já devolve lista para o futuro.
  const current = async (): Promise<JiraConnection | null> => {
    const [first] = await json<ApiConnection[]>(BASE)
    return first ? fromApi(first) : null
  }

  const listProjects = async (refresh = false): Promise<JiraProject[]> => {
    const page = await json<ApiProjectList>(
      `/api/v1/jira/projects${refresh ? '?refresh=true' : ''}`,
    )
    return page.items.map((p) => ({
      key: p.key,
      name: p.name,
      type: p.type,
      avatarUrl: p.avatar_url ?? null,
      openIssues: p.open_issues ?? null,
      totalIssues: p.total_issues ?? null,
      url: p.url,
    }))
  }

  const conversation = (id: string) => `${CONVERSATIONS}/${encodeURIComponent(id)}`

  return {
    ...unavailableProductApi,
    features: { ...unavailableProductApi.features, jira: true, projects: true, chat: CHAT_ENABLED },
    getJiraConnection: current,
    listProjects,
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
        throw Object.assign(new Error('no connection'), { code: 'jira-connection-not-found' })
      return fromApi(
        await json<ApiConnection>(`${BASE}/${existing.id}/validate`, { method: 'POST' }),
      )
    },
    // F07: conversas; F05: o envio em streaming.
    listConversations: async () =>
      (await json<ApiConversationPage>(`${CONVERSATIONS}?limit=${SIDEBAR_LIMIT}`)).items.map(
        conversationFromApi,
      ),
    createConversation: async (projectKey) =>
      conversationFromApi(
        await json<ApiConversation>(CONVERSATIONS, send('POST', { project_key: projectKey })),
      ),
    renameConversation: async (id, title) =>
      conversationFromApi(await json<ApiConversation>(conversation(id), send('PATCH', { title }))),
    pinProject: async (id, projectKey) =>
      conversationFromApi(
        await json<ApiConversation>(conversation(id), send('PATCH', { project_key: projectKey })),
      ),
    deleteConversation: async (id) => {
      await apiFetch(conversation(id), getToken, { method: 'DELETE' })
    },
    getMessages: async (id, cursor) => {
      const query = cursor ? `?limit=50&cursor=${encodeURIComponent(cursor)}` : '?limit=50'
      const page = await json<ApiMessagePage>(`${conversation(id)}/messages${query}`)
      return { items: page.items.map(messageFromApi), nextCursor: page.next_cursor ?? null }
    },
    streamMessage: (id, text, onEvent, signal) =>
      streamPost(
        `${conversation(id ?? 'new')}/messages`,
        { content: text },
        getToken,
        onEvent,
        signal,
      ),
    // F06: confirmar executa no Jira exatamente o que o cartão mostra; recusar não envia nada.
    confirmAction: (id: string) => decide(id, 'confirm'),
    rejectAction: (id: string) => decide(id, 'reject'),
  }
}
