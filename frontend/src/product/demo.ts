import type {
  DocSpace,
  ProjectDocs,
  ChatMessage,
  ConversationSummary,
  CreatedIssue,
  IssueType,
  JiraConnection,
  JiraProject,
  ProductApi,
  ProposedAction,
  IssueReadiness,
} from './types'

const JIRA = 'https://jira.example.com'
const HOUR = 3_600_000

/**
 * Dados de demonstração em memória (F08-RT-08): só em `npm run dev` com `VITE_DEMO_DATA=true` e
 * nos testes. Nunca entram no build de produção (ver `main.tsx`).
 */
export function createDemoProductApi(now: () => number = Date.now): ProductApi {
  let connection: JiraConnection | null = {
    id: 'demo-conexao',
    status: 'ok',
    site: 'jira.example.com',
    email: 'po@example.com',
    accountName: 'Demo PO',
    tokenLast4: '1234',
    validatedAt: new Date(now() - 2 * HOUR).toISOString(),
  }

  const projects: JiraProject[] = [
    ['PAG', 'Payments', 'software', 38, 214],
    ['AUTH', 'Authentication', 'software', 12, 96],
    ['BI', 'Business Intelligence', 'business', 21, 140],
    ['ENT', 'Delivery app', 'software', null, 388],
    ['ATD', 'Customer support', 'service_desk', 9, 61],
  ].map(([key, name, type, openIssues, totalIssues]) => ({
    key: String(key),
    name: String(name),
    type: String(type),
    avatarUrl: null,
    openIssues: openIssues === null ? null : Number(openIssues),
    totalIssues: Number(totalIssues),
    url: `${JIRA}/browse/${String(key)}`,
  }))

  const conversations: ConversationSummary[] = [
    { id: 'c1', title: 'Pix checkout', projectKey: 'PAG', updatedAt: iso(now(), 0) },
    { id: 'c2', title: 'Refine social login', projectKey: 'AUTH', updatedAt: iso(now(), 2) },
    { id: 'c3', title: 'Monthly sales report', projectKey: 'BI', updatedAt: iso(now(), 5) },
  ]

  const action: ProposedAction = {
    id: 'a1',
    kind: 'create_issue',
    projectKey: 'PAG',
    projectName: 'Pagamentos',
    issueKey: null,
    issueType: 'Story',
    title: 'Pay for the order with Pix',
    priority: 'High',
    parentKey: 'PAG-120',
    labels: ['agent-ready', 'specflow'],
    sections: [
      {
        title: 'Objetivo',
        markdown:
          'Como cliente, quero pagar meu pedido com Pix, para concluir a compra sem cartão.',
      },
      {
        title: 'Critérios de aceite',
        markdown:
          '**CA-01 (principal) Gerar cobrança Pix**\nDado estou no checkout com um pedido de R$ 120,00\nQuando escolho "Pix"\nEntão vejo o QR Code e o texto "Pague em até 30 minutos"',
      },
      { title: 'Fora de escopo', markdown: '- Estorno de Pix.\n- Pix parcelado.' },
      { title: 'Como verificar', markdown: '- Testes de unidade da cobrança.\n- E2E do CA-01.' },
    ],
    readiness: {
      ready: true,
      rules: [
        { id: 'P-01', label: 'Título de ação', severity: 'obrigatória', passed: true, detail: '' },
      ],
    },
    conflicts: [{ id: 'RN-04', reason: 'Pix above R$ 5,000 needs the fraud review' }],
    changes: [],
    expiresAt: new Date(now() + 24 * HOUR).toISOString(),
    status: 'pending',
    resultKey: null,
    resultUrl: null,
    error: null,
    errorCode: null,
    doc: null,
    warning: null,
  }

  const messages: Record<string, ChatMessage[]> = {
    c1: [
      {
        id: 'm1',
        role: 'user',
        text: 'I need a story for Pix payments at checkout. The order is confirmed when the bank notifies us.',
        actions: [],
        interrupted: false,
      },
      {
        id: 'm2',
        role: 'assistant',
        text: [
          'I found epic **PAG-120 · New payment methods**. I propose this story as its child:',
          '',
          '### Pay for the order with Pix',
          '',
          'As a store customer, I want to pay with Pix using the QR code, so I can finish checkout without a card.',
          '',
          '```gherkin',
          'Scenario: AC-01 payment confirmed by the bank',
          '  Given I chose Pix at checkout',
          '  When the QR code is shown and I pay',
          '  Then the order changes to "Paid" within 10 seconds',
          '```',
          '',
          '| Criterion | Kind |',
          '|---|---|',
          '| AC-01 | main |',
          '| AC-02 | error |',
        ].join('\n'),
        actions: [action],
        interrupted: false,
      },
    ],
    c2: [],
    c3: [],
  }

  const issues: CreatedIssue[] = [
    issue('PAG-120', 'Epic', 'New payment methods', 30, 'c1', 'Pix checkout', 'agent_ready'),
    issue(
      'AUTH-88',
      'Story',
      'Sign in with a Microsoft account',
      50,
      'c2',
      'Refine social login',
      'agent_ready',
    ),
    issue(
      'AUTH-89',
      'Task',
      'Configure the OIDC provider',
      51,
      'c2',
      'Refine social login',
      'human_only',
    ),
    issue('BI-57', 'Story', 'Export the monthly report as CSV', 98, null, null, 'not_ready'),
  ]

  function issue(
    key: string,
    type: IssueType,
    title: string,
    hoursAgo: number,
    conversationId: string | null,
    conversationTitle: string | null,
    readiness: IssueReadiness,
  ): CreatedIssue {
    const createdAt = new Date(now() - hoursAgo * HOUR).toISOString()
    return {
      key,
      type,
      title,
      projectKey: key.split('-')[0],
      createdAt,
      updatedAt: createdAt,
      operation: 'created',
      readiness,
      url: `${JIRA}/browse/${key}`,
      conversationId,
      conversationTitle,
      hasSpec: true,
    }
  }

  const findAction = (id: string): ProposedAction => {
    if (id !== action.id) throw new Error('action not found')
    return action
  }

  let nextId = 4

  const conversationOf = (id: string): ConversationSummary => {
    const summary = conversations.find((c) => c.id === id)
    if (!summary) throw Object.assign(new Error('not found'), { code: 'conversation-not-found' })
    return summary
  }
  let usedToday = 18
  const docSpaces: DocSpace[] = [
    {
      key: 'PAG',
      name: 'Pagamentos — Documentação',
      url: 'https://demo.atlassian.net/wiki/spaces/PAG',
    },
    { key: 'AUTH', name: 'Autenticação', url: 'https://demo.atlassian.net/wiki/spaces/AUTH' },
  ]
  const docLinks = new Map<string, NonNullable<ProjectDocs['link']>>()

  return {
    features: { jira: true, projects: true, chat: true, usage: true, docs: true },
    demo: true,
    getJiraConnection: async () => connection,
    connectJira: async ({ site, email, token }) => {
      if (token.trim().length < 8) {
        throw Object.assign(new Error('token rejected'), { code: 'jira-invalid-credentials' })
      }
      connection = {
        id: 'demo-conexao',
        status: 'ok',
        site: site.replace(/^https?:\/\//, '').replace(/\/$/, ''),
        email,
        accountName: 'Demo PO',
        tokenLast4: token.trim().slice(-4),
        validatedAt: new Date(now()).toISOString(),
      }
      return connection
    },
    disconnectJira: async () => {
      connection = null
    },
    validateJira: async () => {
      if (!connection) throw Object.assign(new Error('no connection'), { code: 'not-available' })
      connection = { ...connection, validatedAt: new Date(now()).toISOString() }
      return connection
    },
    listProjects: async () => (connection ? projects : []),
    listDocuments: async (projectKey) =>
      [
        {
          pageId: '9001',
          projectKey: 'PAG',
          spaceKey: 'PAG',
          type: 'glossario',
          title: 'Glossário',
          url: 'https://demo.atlassian.net/wiki/spaces/PAG/pages/9001',
          version: 3,
          operation: 'updated' as const,
          createdAt: new Date(now() - 3 * 86_400_000).toISOString(),
          updatedAt: new Date(now() - 3_600_000).toISOString(),
        },
      ].filter((d) => !projectKey || d.projectKey === projectKey),
    listIssues: async (filters) => ({
      items: issues
        .filter(
          (i) =>
            (!filters.projectKey || i.projectKey === filters.projectKey) &&
            (!filters.type || i.type === filters.type) &&
            (!filters.readiness || i.readiness === filters.readiness) &&
            (!filters.from || i.createdAt >= filters.from),
        )
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      nextCursor: null,
    }),
    issueStatuses: async (keys) => {
      const statuses = [
        { name: 'To Do', category: 'new' },
        { name: 'In Progress', category: 'indeterminate' },
        { name: 'Done', category: 'done' },
      ]
      return Object.fromEntries(keys.map((k, n) => [k, statuses[n % statuses.length]]))
    },
    agentPrompt: async (key) => {
      const found = issues.find((i) => i.key === key)
      if (!found) throw Object.assign(new Error('not found'), { code: 'issue-not-found' })
      return [
        `Implemente a issue ${key} abaixo. Os critérios de aceite são os testes de pronto.`,
        `# ${key} · ${found.title}`,
        `Issue no Jira: ${found.url}`,
        '## Critérios de aceite\n\n- Dado …, quando …, então …',
      ].join('\n\n')
    },
    listConversations: async () =>
      [...conversations].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    createConversation: async (projectKey) => {
      const summary = {
        id: `c${nextId++}`,
        title: 'New conversation',
        projectKey,
        updatedAt: new Date(now()).toISOString(),
      }
      conversations.push(summary)
      messages[summary.id] = []
      return { ...summary }
    },
    renameConversation: async (id, title) => {
      const summary = conversationOf(id)
      summary.title = title
      return { ...summary }
    },
    pinProject: async (id, projectKey) => {
      const summary = conversationOf(id)
      summary.projectKey = projectKey
      return { ...summary }
    },
    deleteConversation: async (id) => {
      const index = conversations.findIndex((c) => c.id === id)
      if (index >= 0) conversations.splice(index, 1)
      delete messages[id]
    },
    getMessages: async (id) => ({ items: [...(messages[id] ?? [])], nextCursor: null }),
    streamMessage: async (conversationId, text, onEvent, signal) => {
      let id = conversationId
      if (!id) {
        id = `c${nextId++}`
        conversations.push({
          id,
          title: text.slice(0, 40),
          projectKey: null,
          updatedAt: new Date(now()).toISOString(),
        })
        messages[id] = []
      }
      usedToday += 1
      const reply = 'This is a **demo** reply: the real agent streams its answer here.'
      const user = {
        id: `m${nextId++}`,
        role: 'user' as const,
        text,
        actions: [],
        interrupted: false,
      }
      messages[id].push(user)
      onEvent({ event: 'open', conversation_id: id })
      onEvent({ event: 'tool_start', name: 'listar_projetos', summary: 'Checking Jira projects…' })
      onEvent({ event: 'tool_end', name: 'listar_projetos', summary: 'Done' })
      let sent = ''
      for (const word of reply.split(/(?<= )/)) {
        if (signal?.aborted) break
        sent += word
        onEvent({ event: 'token', text: word })
        await new Promise((resolve) => setTimeout(resolve, 0))
      }
      const assistant = {
        id: `m${nextId++}`,
        role: 'assistant' as const,
        text: sent,
        actions: [],
        interrupted: sent !== reply,
      }
      messages[id].push(assistant)
      conversationOf(id).updatedAt = new Date(now()).toISOString()
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      onEvent({
        event: 'message_saved',
        message_id: assistant.id,
        conversation_id: id,
        user_message_id: user.id,
      })
      onEvent({ event: 'done', usage: { input_tokens: 0, output_tokens: 0, cost_usd: 0 } })
      return { conversationId: id }
    },
    confirmAction: async (id) => {
      const a = findAction(id)
      if (a.status === 'pending') {
        Object.assign(a, {
          status: 'done',
          resultKey: 'PAG-142',
          resultUrl: `${JIRA}/browse/PAG-142`,
        })
        const ready = a.readiness?.ready ? 'agent_ready' : 'not_ready'
        issues.push(
          issue('PAG-142', a.issueType ?? 'Story', a.title, 0, 'c1', 'Pix checkout', ready),
        )
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
      dailyLimit: 20,
      last7Days: [
        { label: 'Sat', count: 12 },
        { label: 'Sun', count: 19 },
        { label: 'Mon', count: 8 },
        { label: 'Tue', count: 0 },
        { label: 'Wed', count: 20 },
        { label: 'Thu', count: 15 },
        { label: 'today', count: usedToday },
      ],
    }),
    getProjectDocs: async (key) => {
      const link = docLinks.get(key) ?? null
      const same = docSpaces.find((d) => d.key === key)
      return {
        link,
        suggestion: !link && same ? { space: same, source: 'same-key' } : null,
        available: true,
      }
    },
    linkProjectDocs: async (key, spaceKey) => {
      const space = docSpaces.find((d) => d.key === spaceKey)
      if (!space)
        throw Object.assign(new Error('not found'), { code: 'confluence-space-not-found' })
      const link = {
        space,
        source: spaceKey === key ? ('same-key' as const) : ('manual' as const),
        linkedAt: new Date(now()).toISOString(),
      }
      docLinks.set(key, link)
      return { link, suggestion: null, available: true }
    },
    unlinkProjectDocs: async (key) => {
      docLinks.delete(key)
    },
    searchDocSpaces: async (query) =>
      docSpaces.filter((d) => `${d.key} ${d.name}`.toLowerCase().includes(query.toLowerCase())),
  }
}

function iso(now: number, hoursAgo: number): string {
  return new Date(now - hoursAgo * HOUR).toISOString()
}
