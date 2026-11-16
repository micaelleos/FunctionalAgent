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
    id: 'demo-conexao',
    status: 'ok',
    site: 'jira.example.com',
    email: 'po@example.com',
    accountName: 'Demo PO',
    tokenLast4: '1234',
    validatedAt: new Date(now() - 2 * HOUR).toISOString(),
  }

  const projects: JiraProject[] = [
    ['PAG', 'Payments', 'Software · Scrum', 38, 214],
    ['AUTH', 'Authentication', 'Software · Kanban', 12, 96],
    ['BI', 'Business Intelligence', 'Software · Scrum', 21, 140],
    ['ENT', 'Delivery app', 'Software · Scrum', 54, 388],
    ['ATD', 'Customer support', 'Service management', 9, 61],
  ].map(([key, name, type, openIssues, totalIssues]) => ({
    key: String(key),
    name: String(name),
    type: String(type),
    openIssues: Number(openIssues),
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
    projectKey: 'PAG',
    projectName: 'Pagamentos',
    issueType: 'Story',
    title: 'Pay for the order with Pix',
    priority: 'High',
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
            text: 'I need a story for Pix payments at checkout. The order is confirmed when the bank notifies us.',
          },
        ],
      },
      {
        id: 'm2',
        role: 'assistant',
        parts: [
          { kind: 'tool', label: 'Looked up project PAG in Jira' },
          {
            kind: 'text',
            text: 'I found epic PAG-120 · New payment methods. I propose this story as its child:',
          },
          { kind: 'heading', text: 'Pay for the order with Pix' },
          {
            kind: 'text',
            text: 'As a store customer, I want to pay with Pix using the QR code, so I can finish checkout without a card.',
          },
          {
            kind: 'code',
            text: [
              'Scenario: AC-01 payment confirmed by the bank',
              '  Given I chose Pix at checkout',
              '  When the QR code is shown and I pay',
              '  Then the order changes to "Paid" within 10 seconds',
              '',
              'Scenario: AC-02 expired QR code (error)',
              '  Given the QR code was generated 30 minutes ago',
              '  When I try to pay',
              '  Then I see "Code expired" and can generate a new one',
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
    issue('PAG-120', 'Epic', 'New payment methods', 30, 'c1', 'Pix checkout'),
    issue('AUTH-88', 'Story', 'Sign in with a Microsoft account', 50, 'c2', 'Refine social login'),
    issue('AUTH-89', 'Task', 'Configure the OIDC provider', 51, 'c2', 'Refine social login'),
    issue('BI-57', 'Story', 'Export the monthly report as CSV', 98, 'c3', 'Monthly sales report'),
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
    if (id !== action.id) throw new Error('action not found')
    return action
  }

  let nextId = 4
  let usedToday = 18

  return {
    features: { jira: true, projects: true, chat: true, usage: true },
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
    listIssues: async () => [...issues].sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    refreshIssueStatuses: async () => {
      const statuses = ['To Do', 'In Progress', 'Done']
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
              text: 'This is a demo: the real agent arrives in F05. Replies will stream in here.',
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
        issues.push(issue('PAG-142', a.issueType, a.title, 0, 'c1', 'Pix checkout'))
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
        { label: 'Sat', count: 12 },
        { label: 'Sun', count: 31 },
        { label: 'Mon', count: 8 },
        { label: 'Tue', count: 0 },
        { label: 'Wed', count: 44 },
        { label: 'Thu', count: 27 },
        { label: 'today', count: usedToday },
      ],
    }),
  }
}

function iso(now: number, hoursAgo: number): string {
  return new Date(now - hoursAgo * HOUR).toISOString()
}
