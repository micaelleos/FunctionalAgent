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
  /** F19: vincular o projeto a um espaço do Confluence. */
  docs: boolean
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

/** Prontidão gravada nas labels: `agent-ready`, `human-only` ou nenhuma das duas (F10-RF-07). */
export type IssueReadiness = 'agent_ready' | 'human_only' | 'not_ready'

export interface CreatedIssue {
  key: string
  /** Tipo no momento da gravação (Epic, Story, Task); vazio se o SpecFlow só atualizou campos. */
  type: string
  title: string
  projectKey: string
  /** Quando o SpecFlow tocou na issue pela 1ª vez. */
  createdAt: string
  updatedAt: string | null
  /** `updated`: o SpecFlow só atualizou uma issue que já existia. */
  operation: 'created' | 'updated'
  readiness: IssueReadiness
  url: string
  /** `null` se a conversa de origem foi excluída (F10-RT-03). */
  conversationId: string | null
  conversationTitle: string | null
  /** Há spec guardada para "Copiar para agente de código" (F10-RF-06). */
  hasSpec: boolean
}

export interface IssueFilters {
  projectKey?: string
  type?: IssueType
  readiness?: IssueReadiness
  /** ISO; início do período (inclusivo). */
  from?: string
}

export interface IssuePage {
  items: CreatedIssue[]
  nextCursor: string | null
}

/** Status atual no Jira; `null` quando a issue não existe mais (ou a conta não a vê). */
export type IssueStatus = { name: string; category: string } | null

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

export interface DocSpace {
  key: string
  name: string
  url: string
}

/** Vínculo do projeto com o espaço do Confluence ou, sem vínculo, a sugestão (F19-RF-01/02). */
export interface ProjectDocs {
  link: { space: DocSpace; source: 'same-key' | 'label' | 'manual'; linkedAt: string } | null
  suggestion: { space: DocSpace; source: 'same-key' | 'label' } | null
  /** `false`: a conta não tem acesso ao Confluence do site (F19-RF-09). */
  available: boolean
  /** Sem espaço e com a escrita ligada: o agente pode criar o espaço (F20-RF-01). */
  canCreate?: boolean
}

/** Regra, ADR ou artigo da documentação do projeto que a proposta contradiz (F19-RF-07). */
export interface DocConflict {
  id: string
  reason: string
}

/** Página do Confluence escrita pelo SpecFlow (F20-RF-08). */
export interface DocRecord {
  pageId: string
  projectKey: string | null
  spaceKey: string | null
  type: string
  title: string
  url: string
  version: number
  operation: 'created' | 'updated'
  createdAt: string
  updatedAt: string
}

/** Seção da página que a proposta muda (F20-RT-04): o cartão mostra antes → depois. */
export interface PageDiff {
  section: string
  change: 'added' | 'removed' | 'changed'
  before: string
  after: string
}

/** Proposta de escrita no Confluence (F20): página nova, atualização ou espaço com o modelo. */
export interface DocProposal {
  /** Tipo do modelo da metodologia (`glossario`, `adr`…); vazio na criação do espaço. */
  pageType: string
  summary: string
  space: DocSpace | null
  parentTitle: string | null
  /** Atualização: link da página atual, versão vista e o título anterior, se mudou. */
  url: string | null
  version: number | null
  previousTitle: string | null
  diff: PageDiff[]
  /** Criação do espaço: chave e títulos das páginas do modelo. */
  spaceKey: string | null
  pages: string[]
}

export type ActionKind =
  | 'create_issue'
  | 'update_issue'
  | 'create_page'
  | 'update_page'
  | 'create_space'

export const DOC_KINDS: readonly ActionKind[] = ['create_page', 'update_page', 'create_space']

/** Ação proposta pelo agente; só vira escrita no Jira/Confluence depois de confirmada (ADR-003). */
export interface ProposedAction {
  id: string
  kind: ActionKind
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
  /** Avisos de conflito com a documentação no Confluence; não mudam o que vai ao Jira. */
  conflicts: DocConflict[]
  changes: FieldChange[]
  expiresAt: string
  status: ActionStatus
  resultKey: string | null
  resultUrl: string | null
  /** Erro do Jira já traduzido pela API (F06-RF-07). */
  error: string | null
  /** Código do erro (ex.: `confluence-version-conflict`), para a mensagem do cartão. */
  errorCode: string | null
  /** Só nas ações do Confluence (F20). */
  doc: DocProposal | null
  /** Aviso da execução (ex.: o Registro de mudanças não foi atualizado). */
  warning: string | null
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
  /** Do mais recente ao mais antigo, filtrado no servidor (F10-RF-01, RF-03). */
  listIssues(filters: IssueFilters, cursor?: string | null): Promise<IssuePage>
  /** Páginas do Confluence escritas pelo SpecFlow (F20-RF-08). */
  listDocuments(projectKey?: string): Promise<DocRecord[]>
  /** Até 50 chaves numa chamada (F10-RF-05). */
  issueStatuses(keys: string[]): Promise<Record<string, IssueStatus>>
  /** Texto para colar no agente de código (F10-RF-06). */
  agentPrompt(key: string): Promise<string>
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
  getProjectDocs(projectKey: string): Promise<ProjectDocs>
  linkProjectDocs(projectKey: string, spaceKey: string): Promise<ProjectDocs>
  unlinkProjectDocs(projectKey: string): Promise<void>
  /** Até 25 espaços do site, filtrados por nome ou chave. */
  searchDocSpaces(query: string): Promise<DocSpace[]>
}
