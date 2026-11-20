import { apiFetch, type TokenGetter } from '../lib/api'
import type { components } from '../lib/api-schema'
import { streamPost } from '../lib/sse'
import type {
  ChatMessage,
  ConversationSummary,
  CreatedIssue,
  DocSpace,
  IssueFilters,
  IssueStatus,
  JiraConnection,
  JiraConnectionInput,
  JiraProject,
  ProductApi,
  ProjectDocs,
  Usage,
} from './types'
import { type ApiAction, fromApiAction, toActionProblem } from './actions'
import { unavailableProductApi } from './unavailable'

type ApiConnection = components['schemas']['JiraConnection']
type ApiConversation = components['schemas']['ConversationOut']
type ApiConversationPage = components['schemas']['ConversationPage']
type ApiMessagePage = components['schemas']['MessagePage']
type ApiMessage = components['schemas']['MessageOut']
type ApiProjectList = components['schemas']['JiraProjectList']
type ApiIssue = components['schemas']['IssueOut']
type ApiIssuePage = components['schemas']['IssuePage']
type ApiStatuses = components['schemas']['StatusOut']
type ApiPrompt = components['schemas']['AgentPrompt']
type ApiUsage = components['schemas']['UsageOut']
type ApiProjectDocs = components['schemas']['ProjectConfluenceOut']
type ApiDocument = components['schemas']['DocumentOut']
type ApiLink = components['schemas']['ConfluenceLinkOut']
type ApiSpace = components['schemas']['ConfluenceSpaceOut']

const ISSUES = '/api/v1/jira/issues'
const ISSUE_PAGE = 25

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

const issueFromApi = (i: ApiIssue): CreatedIssue => ({
  key: i.key,
  type: i.issue_type,
  title: i.summary,
  projectKey: i.project_key,
  createdAt: i.created_at,
  updatedAt: i.updated_at ?? null,
  operation: i.operation,
  readiness: i.readiness,
  url: i.url,
  conversationId: i.conversation_id ?? null,
  conversationTitle: i.conversation_title ?? null,
  hasSpec: i.has_spec,
})

const issueQuery = (filters: IssueFilters, cursor?: string | null): string => {
  const params = new URLSearchParams({ limit: String(ISSUE_PAGE) })
  if (filters.projectKey) params.set('project', filters.projectKey)
  if (filters.type) params.set('type', filters.type)
  if (filters.readiness) params.set('readiness', filters.readiness)
  if (filters.from) params.set('from', filters.from)
  if (cursor) params.set('cursor', cursor)
  return `${ISSUES}?${params.toString()}`
}

const weekday = (day: string) =>
  new Date(`${day}T12:00:00Z`).toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' })

/** Uso do dia (F11-RF-01); o último dos 7 dias é hoje (dia de Brasília). */
export const usageFromApi = (u: ApiUsage): Usage => ({
  usedToday: u.messages_today,
  dailyLimit: u.message_limit,
  last7Days: u.last_7_days.map((d, i, all) => ({
    label: i === all.length - 1 ? 'today' : weekday(d.day),
    count: d.messages,
  })),
})

const spaceFromApi = (s: ApiSpace): DocSpace => ({ key: s.key, name: s.name, url: s.url })
const linkFromApi = (l: ApiLink): NonNullable<ProjectDocs['link']> => ({
  space: spaceFromApi(l.space),
  source: l.source,
  linkedAt: l.linked_at,
})
export const projectDocsFromApi = (d: ApiProjectDocs): ProjectDocs => ({
  link: d.link ? linkFromApi(d.link) : null,
  suggestion: d.suggestion
    ? { space: spaceFromApi(d.suggestion.space), source: d.suggestion.source }
    : null,
  available: d.available ?? true,
  canCreate: d.can_create ?? false,
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

  const projectDocs = (key: string) => `/api/v1/jira/projects/${encodeURIComponent(key)}/confluence`
  const conversation = (id: string) => `${CONVERSATIONS}/${encodeURIComponent(id)}`

  return {
    ...unavailableProductApi,
    features: {
      ...unavailableProductApi.features,
      jira: true,
      projects: true,
      chat: CHAT_ENABLED,
      usage: true,
      docs: true,
    },
    // F19: documentação do projeto no Confluence.
    getProjectDocs: async (key) => projectDocsFromApi(await json<ApiProjectDocs>(projectDocs(key))),
    linkProjectDocs: async (key, spaceKey) => ({
      link: linkFromApi(
        await json<ApiLink>(projectDocs(key), send('PUT', { space_key: spaceKey })),
      ),
      suggestion: null,
      available: true,
    }),
    unlinkProjectDocs: async (key) => {
      await apiFetch(projectDocs(key), getToken, { method: 'DELETE' })
    },
    searchDocSpaces: async (query) =>
      (
        await json<ApiSpace[]>(`/api/v1/confluence/spaces?${new URLSearchParams({ q: query })}`)
      ).map(spaceFromApi),
    // F11: consumo do dia e limite.
    getUsage: async () => usageFromApi(await json<ApiUsage>('/api/v1/me/usage')),
    getJiraConnection: current,
    listProjects,
    // F10: histórico de issues.
    listDocuments: async (projectKey) => {
      const query = projectKey ? `?project=${encodeURIComponent(projectKey)}` : ''
      const docs = await json<ApiDocument[]>(`/api/v1/documents${query}`)
      return docs.map((d) => ({
        pageId: d.page_id,
        projectKey: d.project_key ?? null,
        spaceKey: d.space_key ?? null,
        type: d.type,
        title: d.title,
        url: d.url,
        version: d.version,
        operation: d.operation,
        createdAt: d.created_at,
        updatedAt: d.updated_at,
      }))
    },
    listIssues: async (filters, cursor) => {
      const page = await json<ApiIssuePage>(issueQuery(filters, cursor))
      return { items: page.items.map(issueFromApi), nextCursor: page.next_cursor ?? null }
    },
    issueStatuses: async (keys) => {
      const out = await json<ApiStatuses>(`${ISSUES}/status`, send('POST', { keys }))
      return Object.fromEntries(
        Object.entries(out.statuses).map(([k, v]): [string, IssueStatus] => [k, v ?? null]),
      )
    },
    agentPrompt: async (key) =>
      (await json<ApiPrompt>(`${ISSUES}/${encodeURIComponent(key)}/agent-prompt`)).text,
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
