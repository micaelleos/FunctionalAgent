import type {
  ChatMessage,
  ConversationSummary,
  CreatedIssue,
  JiraConnection,
  JiraProject,
  ProductApi,
  ProposedAction,
} from './types'

const JIRA = 'https://jira.example.com'
const HOUR = 3_600_000

/**
 * Dados de demonstração em memória (F08-RT-08): só em `npm run dev` com `VITE_DEMO_DATA=true` e
 * nos testes. Nunca entram no build de produção (ver `main.tsx`).
 */
export function createDemoProductApi(now: () => number = Date.now): ProductApi {
  let connection: JiraConnection | null = {
    site: 'jira.example.com',
    email: 'po@example.com',
    accountName: 'PO de demonstração',
    tokenLast4: '1234',
    validatedAt: new Date(now() - 2 * HOUR).toISOString(),
  }

  const projects: JiraProject[] = [
    ['PAG', 'Pagamentos', 'Software · Scrum', 38, 214],
    ['AUTH', 'Autenticação', 'Software · Kanban', 12, 96],
    ['BI', 'Business Intelligence', 'Software · Scrum', 21, 140],
    ['ENT', 'App de entregas', 'Software · Scrum', 54, 388],
    ['ATD', 'Atendimento', 'Gestão de serviços', 9, 61],
  ].map(([key, name, type, openIssues, totalIssues]) => ({
    key: String(key),
    name: String(name),
    type: String(type),
    openIssues: Number(openIssues),
    totalIssues: Number(totalIssues),
    url: `${JIRA}/browse/${String(key)}`,
  }))

  const conversations: ConversationSummary[] = [
    { id: 'c1', title: 'Checkout com Pix', projectKey: 'PAG', updatedAt: iso(now(), 0) },
    { id: 'c2', title: 'Refinar login social', projectKey: 'AUTH', updatedAt: iso(now(), 2) },
    { id: 'c3', title: 'Relatório de vendas mensal', projectKey: 'BI', updatedAt: iso(now(), 5) },
  ]

  const action: ProposedAction = {
    id: 'a1',
    projectKey: 'PAG',
    projectName: 'Pagamentos',
    issueType: 'História',
    title: 'Pagar o pedido com Pix',
    priority: 'Alta',
    parentKey: 'PAG-120',
    expiresAt: new Date(now() + 24 * HOUR).toISOString(),
    status: 'pending',
    resultKey: null,
    resultUrl: null,
  }

  const messages: Record<string, ChatMessage[]> = {
    c1: [
      {
        id: 'm1',
        role: 'user',
        parts: [
          {
            kind: 'text',
            text: 'Preciso de uma história para o pagamento com Pix no checkout. O pedido é confirmado quando o banco avisa.',
          },
        ],
      },
      {
        id: 'm2',
        role: 'assistant',
        parts: [
          { kind: 'tool', label: 'Consultou o projeto PAG no Jira' },
          {
            kind: 'text',
            text: 'Encontrei o épico PAG-120 · Novos meios de pagamento. Proponho esta história como filha dele:',
          },
          { kind: 'heading', text: 'Pagar o pedido com Pix' },
          {
            kind: 'text',
            text: 'Como cliente da loja, quero pagar com Pix pelo QR Code, para concluir a compra sem cartão.',
          },
          {
            kind: 'code',
            text: [
              'Cenário: pagamento confirmado pelo banco',
              '  Dado que escolhi Pix no checkout',
              '  Quando o QR Code é exibido e eu pago',
              '  Então o pedido muda para "Pago" em até 10 segundos',
              '',
              'Cenário: QR Code expirado',
              '  Dado que o QR Code foi gerado há 30 minutos',
              '  Quando tento pagar',
              '  Então vejo "Código expirado" e posso gerar outro',
            ].join('\n'),
          },
          { kind: 'action', action },
        ],
      },
    ],
    c2: [],
    c3: [],
  }

  const issues: CreatedIssue[] = [
    issue('PAG-120', 'Épico', 'Novos meios de pagamento', 30, 'c1', 'Checkout com Pix'),
    issue('AUTH-88', 'História', 'Entrar com conta Microsoft', 50, 'c2', 'Refinar login social'),
    issue('AUTH-89', 'Tarefa', 'Configurar provedor OIDC', 51, 'c2', 'Refinar login social'),
    issue('BI-57', 'História', 'Exportar relatório mensal em CSV', 98, 'c3', 'Relatório de vendas'),
  ]

  function issue(
    key: string,
    type: CreatedIssue['type'],
    title: string,
    hoursAgo: number,
    conversationId: string,
    conversationTitle: string,
  ): CreatedIssue {
    return {
      key,
      type,
      title,
      projectKey: key.split('-')[0],
      status: null,
      createdAt: new Date(now() - hoursAgo * HOUR).toISOString(),
      url: `${JIRA}/browse/${key}`,
      conversationId,
      conversationTitle,
    }
  }

  const findAction = (id: string): ProposedAction => {
    if (id !== action.id) throw new Error('ação não encontrada')
    return action
  }

  let nextId = 4
  let usedToday = 18

  return {
    features: { jira: true, chat: true, usage: true },
    demo: true,
    getJiraConnection: async () => connection,
    connectJira: async ({ site, email, token }) => {
      if (token.trim().length < 8) {
        throw Object.assign(new Error('token recusado'), { code: 'jira-invalid-credentials' })
      }
      connection = {
        site: site.replace(/^https?:\/\//, '').replace(/\/$/, ''),
        email,
        accountName: 'PO de demonstração',
        tokenLast4: token.trim().slice(-4),
        validatedAt: new Date(now()).toISOString(),
      }
      return connection
    },
    disconnectJira: async () => {
      connection = null
    },
    listProjects: async () => (connection ? projects : []),
    listIssues: async () => [...issues].sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    refreshIssueStatuses: async () => {
      const statuses = ['A fazer', 'Em andamento', 'Concluído']
      issues.forEach((i, n) => (i.status = statuses[n % statuses.length]))
      return [...issues].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    },
    listConversations: async () =>
      [...conversations].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    getMessages: async (id) => messages[id] ?? [],
    sendMessage: async (conversationId, text, projectKey) => {
      let id = conversationId
      if (!id) {
        id = `c${nextId++}`
        conversations.push({
          id,
          title: text.slice(0, 40),
          projectKey,
          updatedAt: new Date(now()).toISOString(),
        })
        messages[id] = []
      }
      usedToday += 1
      messages[id].push(
        { id: `m${nextId++}`, role: 'user', parts: [{ kind: 'text', text }] },
        {
          id: `m${nextId++}`,
          role: 'assistant',
          parts: [
            {
              kind: 'text',
              text: 'Isto é uma demonstração: o agente de verdade chega na F05. As respostas vão aparecer aqui em streaming.',
            },
          ],
        },
      )
      const summary = conversations.find((c) => c.id === id)
      if (summary) summary.updatedAt = new Date(now()).toISOString()
      return { conversationId: id }
    },
    confirmAction: async (id) => {
      const a = findAction(id)
      if (a.status === 'pending') {
        Object.assign(a, {
          status: 'confirmed',
          resultKey: 'PAG-142',
          resultUrl: `${JIRA}/browse/PAG-142`,
        })
        issues.push(issue('PAG-142', a.issueType, a.title, 0, 'c1', 'Checkout com Pix'))
      }
      return { ...a }
    },
    rejectAction: async (id) => {
      const a = findAction(id)
      if (a.status === 'pending') a.status = 'rejected'
      return { ...a }
    },
    getUsage: async () => ({
      usedToday,
      dailyLimit: 50,
      last7Days: [
        { label: 'sáb', count: 12 },
        { label: 'dom', count: 31 },
        { label: 'seg', count: 8 },
        { label: 'ter', count: 0 },
        { label: 'qua', count: 44 },
        { label: 'qui', count: 27 },
        { label: 'hoje', count: usedToday },
      ],
    }),
  }
}

function iso(now: number, hoursAgo: number): string {
  return new Date(now - hoursAgo * HOUR).toISOString()
}
