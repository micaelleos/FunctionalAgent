import type { ProductApi } from './types'

/** Lançado quando a tela chama algo cuja feature ainda não está no ar. */
export class NotAvailableError extends Error {
  readonly code = 'not-available'

  constructor(feature: string) {
    super(`${feature} is not available yet`)
    this.name = 'NotAvailableError'
  }
}

/**
 * Produção enquanto F04–F11 não existem: listas vazias e nenhum dado inventado (F08-RT-08).
 * Cada feature substitui os métodos dela pela chamada à API real.
 */
export const unavailableProductApi: ProductApi = {
  features: { jira: false, projects: false, chat: false, usage: false },
  demo: false,
  getJiraConnection: async () => null,
  connectJira: async () => {
    throw new NotAvailableError('The Jira connection')
  },
  disconnectJira: async () => {
    throw new NotAvailableError('The Jira connection')
  },
  validateJira: async () => {
    throw new NotAvailableError('The Jira connection')
  },
  listProjects: async () => [],
  listIssues: async () => [],
  refreshIssueStatuses: async () => [],
  listConversations: async () => [],
  createConversation: async () => {
    throw new NotAvailableError('Conversations')
  },
  renameConversation: async () => {
    throw new NotAvailableError('Conversations')
  },
  pinProject: async () => {
    throw new NotAvailableError('Conversations')
  },
  deleteConversation: async () => {
    throw new NotAvailableError('Conversations')
  },
  getMessages: async () => ({ items: [], nextCursor: null }),
  streamMessage: async () => {
    throw new NotAvailableError('The agent')
  },
  confirmAction: async () => {
    throw new NotAvailableError('Action confirmation')
  },
  rejectAction: async () => {
    throw new NotAvailableError('Action confirmation')
  },
  getUsage: async () => null,
}
