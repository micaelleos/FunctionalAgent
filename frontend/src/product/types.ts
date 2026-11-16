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

export type IssueType = 'Épico' | 'História' | 'Tarefa'

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

export type ActionStatus = 'pending' | 'confirmed' | 'rejected' | 'expired'

/** Ação proposta pelo agente; só vira escrita no Jira depois de confirmada (ADR-003, F06). */
export interface ProposedAction {
  id: string
  projectKey: string
  projectName: string
  issueType: IssueType
  title: string
  priority: string
  parentKey: string | null
  expiresAt: string
  status: ActionStatus
  resultKey: string | null
  resultUrl: string | null
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
