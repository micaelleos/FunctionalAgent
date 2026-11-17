/**
 * Dados das telas principais (F08-RF-10).
 *
 * As telas falam só com esta interface. Hoje há duas implementações:
 * - `unavailableProductApi`: produção, enquanto F04–F11 não estão no ar. Devolve estados vazios
 *   e diz quais recursos ainda não existem; nunca mostra dados inventados (F08-RT-08);
 * - `createDemoProductApi`: dados de demonstração em memória, só em `npm run dev` com
 *   `VITE_DEMO_DATA=true` e nos testes.
 * - `createHttpProductApi`: produção; liga o que já existe no backend (F04: conexão Jira) e usa
 *   `unavailableProductApi` no resto.
 * Cada feature troca o seu pedaço pela chamada HTTP ao endpoint `/api/v1/...` dela.
 */

export interface Features {
  /** F04: conectar, trocar e remover a conta do Jira. */
  jira: boolean
  /** F09: listar os projetos do Jira. */
  projects: boolean
  /** F05–F07: conversar com o agente e guardar as conversas. */
  chat: boolean
  /** F11: uso diário e limite. */
  usage: boolean
}

/** `invalid`: o Jira recusou o token guardado; o app pede reconexão (F04-RF-06). */
export type JiraConnectionStatus = 'ok' | 'invalid'

export interface JiraConnection {
  id: string
  /** Host do site, sem `https://` (ex.: `sua-empresa.atlassian.net`). */
  site: string
  email: string
  accountName: string
  tokenLast4: string
  validatedAt: string
  status: JiraConnectionStatus
}

export interface JiraConnectionInput {
  site: string
  email: string
  token: string
}

export interface JiraProject {
  key: string
  name: string
  type: string
  openIssues: number
  totalIssues: number
  url: string
}

export type IssueType = 'Epic' | 'Story' | 'Task'

export interface CreatedIssue {
  key: string
  type: IssueType
  title: string
  projectKey: string
  /** Status atual no Jira; só existe depois de "Atualizar status" (F10). */
  status: string | null
  createdAt: string
  url: string
  conversationId: string
  conversationTitle: string
}

export interface ConversationSummary {
  id: string
  title: string
  projectKey: string | null
  updatedAt: string
}

/** Estados da ação na API (F06): `executing` dura o tempo da chamada ao Jira. */
export type ActionStatus = 'pending' | 'executing' | 'done' | 'failed' | 'rejected' | 'expired'

export interface SpecSection {
  title: string
  markdown: string
}

export interface ReadinessRule {
  id: string
  label: string
  /** `obrigatória` tira a label `agent-ready`; `aviso` só informa. */
  severity: string
  passed: boolean
  detail: string
}

export interface Readiness {
  ready: boolean
  rules: ReadinessRule[]
}

/** Antes/depois de um campo numa atualização (F06-RF-06). */
export interface FieldChange {
  field: 'summary' | 'description' | 'priority' | 'labels'
  before: string
  after: string
}

/** Ação proposta pelo agente; só vira escrita no Jira depois de confirmada (ADR-003, F06). */
export interface ProposedAction {
  id: string
  kind: 'create_issue' | 'update_issue'
  /** Criação: projeto de destino. Atualização: `null` (vale `issueKey`). */
  projectKey: string | null
  projectName: string
  issueKey: string | null
  issueType: IssueType | null
  title: string
  /** `null`: sem prioridade na proposta (vale o padrão do projeto). */
  priority: string | null
  parentKey: string | null
  labels: string[]
  /** A spec por seção, na ordem fixa (F06-RF-01). */
  sections: SpecSection[]
  readiness: Readiness | null
  changes: FieldChange[]
  expiresAt: string
  status: ActionStatus
  resultKey: string | null
  resultUrl: string | null
  /** Erro do Jira já traduzido pela API (F06-RF-07). */
  error: string | null
}

export type MessagePart =
  | { kind: 'text'; text: string }
  | { kind: 'heading'; text: string }
  | { kind: 'code'; text: string }
  | { kind: 'tool'; label: string }
  | { kind: 'action'; action: ProposedAction }

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  parts: MessagePart[]
}

export interface Usage {
  usedToday: number
  dailyLimit: number
  last7Days: { label: string; count: number }[]
}

export interface ProductApi {
  features: Features
  /** `true` quando os dados são de demonstração; a interface mostra um aviso. */
  demo: boolean
  getJiraConnection(): Promise<JiraConnection | null>
  connectJira(input: JiraConnectionInput): Promise<JiraConnection>
  disconnectJira(): Promise<void>
  /** Testa a credencial guardada; se o Jira recusar, a conexão volta com `status: 'invalid'`. */
  validateJira(): Promise<JiraConnection>
  listProjects(): Promise<JiraProject[]>
  listIssues(): Promise<CreatedIssue[]>
  refreshIssueStatuses(): Promise<CreatedIssue[]>
  listConversations(): Promise<ConversationSummary[]>
  getMessages(conversationId: string): Promise<ChatMessage[]>
  sendMessage(
    conversationId: string | null,
    text: string,
    projectKey: string | null,
  ): Promise<{
    conversationId: string
  }>
  confirmAction(actionId: string): Promise<ProposedAction>
  rejectAction(actionId: string): Promise<ProposedAction>
  getUsage(): Promise<Usage | null>
}
