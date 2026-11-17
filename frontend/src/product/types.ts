import type { ChatEvent } from '../lib/sse'

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
  /** `projectTypeKey` do Jira: `software`, `business`, `service_desk`. */
  type: string
  /** Avatar do Jira (https); a tela mostra as iniciais se não carregar. */
  avatarUrl: string | null
  /** `null`: o Jira não respondeu a contagem (a tela mostra "—", F09-RT-04). */
  openIssues: number | null
  totalIssues: number | null
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

/** Mensagem do histórico (F07): o texto em Markdown e os cartões das ações propostas nela. */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  actions: ProposedAction[]
  /** O usuário parou a resposta no meio (F08-RF-06): o texto é parcial. */
  interrupted: boolean
}

/** Uma página do histórico, da mais antiga para a mais nova; `nextCursor` leva às anteriores. */
export interface MessagePage {
  items: ChatMessage[]
  nextCursor: string | null
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
  /** `refresh` ignora o cache de 5 min do backend (F09-RF-07). */
  listProjects(refresh?: boolean): Promise<JiraProject[]>
  listIssues(): Promise<CreatedIssue[]>
  refreshIssueStatuses(): Promise<CreatedIssue[]>
  listConversations(): Promise<ConversationSummary[]>
  /** Conversa vazia com o projeto fixado (F07-RF-06); sem projeto, o 1º envio já cria. */
  createConversation(projectKey: string | null): Promise<ConversationSummary>
  renameConversation(conversationId: string, title: string): Promise<ConversationSummary>
  pinProject(conversationId: string, projectKey: string | null): Promise<ConversationSummary>
  deleteConversation(conversationId: string): Promise<void>
  getMessages(conversationId: string, cursor?: string | null): Promise<MessagePage>
  /**
   * Envia e acompanha a resposta em streaming (F08-RF-01). `conversationId: null` cria a conversa.
   * `signal` interrompe ("Parar"); erros antes do stream são lançados.
   */
  streamMessage(
    conversationId: string | null,
    text: string,
    onEvent: (event: ChatEvent) => void,
    signal?: AbortSignal,
  ): Promise<{ conversationId: string }>
  confirmAction(actionId: string): Promise<ProposedAction>
  rejectAction(actionId: string): Promise<ProposedAction>
  getUsage(): Promise<Usage | null>
}
