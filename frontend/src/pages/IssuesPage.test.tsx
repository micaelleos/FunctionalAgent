import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { createDemoProductApi } from '../product/demo'
import type { CreatedIssue, IssueFilters, ProductApi } from '../product/types'
import { ALICE, fakeAuth } from '../test/fakeAuth'

afterEach(() => vi.restoreAllMocks())

const NOW = Date.parse('2026-11-17T12:00:00Z')
const SITE = 'https://sandbox.atlassian.net'

const issue = (key: string, extra: Partial<CreatedIssue> = {}): CreatedIssue => ({
  key,
  type: 'Story',
  title: `Título ${key}`,
  projectKey: key.split('-')[0],
  createdAt: '2026-11-16T10:00:00Z',
  updatedAt: null,
  operation: 'created',
  readiness: 'agent_ready',
  url: `${SITE}/browse/${key}`,
  conversationId: 'c1',
  conversationTitle: 'Pix checkout',
  hasSpec: true,
  ...extra,
})

function setup(items: CreatedIssue[], more: CreatedIssue[] = []) {
  const api: ProductApi = createDemoProductApi(() => NOW)
  const calls: { filters: IssueFilters; cursor: string | null | undefined }[] = []
  api.listIssues = async (filters, cursor) => {
    calls.push({ filters, cursor })
    if (cursor === 'p2') return { items: more, nextCursor: null }
    return { items, nextCursor: more.length ? 'p2' : null }
  }
  render(<App authClient={fakeAuth(ALICE).client} productApi={api} initialPath="/issues" />)
  return { api, calls, user: userEvent.setup() }
}

const row = (key: string) =>
  screen.getByRole('link', { name: key }).closest('tr') as HTMLTableRowElement

describe('F10-RF-01 F10-RF-04 lista de issues', () => {
  it('mostra as issues com link do Jira, origem e marca de só atualizada', async () => {
    setup([
      issue('ABC-2'),
      issue('OLD-3', { operation: 'updated', type: '', hasSpec: false, conversationId: null }),
    ])

    const link = await screen.findByRole('link', { name: 'ABC-2' })
    expect(link).toHaveAttribute('href', `${SITE}/browse/ABC-2`)
    expect(link).toHaveAttribute('target', '_blank')
    expect(within(row('ABC-2')).getByRole('link', { name: 'Pix checkout' })).toHaveAttribute(
      'href',
      '/chat/c1',
    )
    const old = row('OLD-3')
    expect(within(old).getByText('updated')).toBeInTheDocument()
    expect(within(old).getByText('Conversation deleted')).toBeInTheDocument()
    expect(within(old).getByText('No spec to copy')).toBeInTheDocument()
  })

  it('"Load more" pede a página seguinte pelo cursor', async () => {
    const { calls, user } = setup([issue('ABC-2')], [issue('ABC-1')])

    await user.click(await screen.findByRole('button', { name: 'Load more' }))

    expect(await screen.findByRole('link', { name: 'ABC-1' })).toBeInTheDocument()
    expect(calls.map((c) => c.cursor)).toEqual([null, 'p2'])
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
  })
})

describe('F10-RF-03 F10-RF-07 filtros no servidor', () => {
  it('projeto, tipo, prontidão e período vão para a API', async () => {
    const { calls, user } = setup([issue('ABC-2'), issue('XYZ-1')])
    await screen.findByRole('link', { name: 'ABC-2' })

    await user.selectOptions(screen.getByLabelText('Project'), 'XYZ')
    await user.click(screen.getByRole('button', { name: 'Epic' }))
    await user.selectOptions(screen.getByLabelText('Readiness'), 'human_only')
    await user.selectOptions(screen.getByLabelText('Period'), '7')

    await waitFor(() => expect(calls).toHaveLength(5))
    const last = calls[4].filters
    expect(last).toMatchObject({ projectKey: 'XYZ', type: 'Epic', readiness: 'human_only' })
    expect(Date.parse(last.from ?? '')).toBeGreaterThan(Date.now() - 8 * 86_400_000)
  })

  it('mostra o selo de prontidão', async () => {
    setup([issue('ABC-2'), issue('ABC-3', { readiness: 'human_only' })])

    await screen.findByRole('link', { name: 'ABC-2' })
    expect(within(row('ABC-2')).getByText('Agent-ready')).toBeInTheDocument()
    expect(within(row('ABC-3')).getByText('Human-only')).toBeInTheDocument()
  })

  it('filtro sem resultado mostra a mensagem, não o estado vazio', async () => {
    const { api, user } = setup([issue('ABC-2')])
    await screen.findByRole('link', { name: 'ABC-2' })
    api.listIssues = async () => ({ items: [], nextCursor: null })

    await user.click(screen.getByRole('button', { name: 'Task' }))

    expect(await screen.findByText('No issues match these filters.')).toBeInTheDocument()
    expect(screen.queryByText(/No issues yet/)).not.toBeInTheDocument()
  })
})

describe('F10-RF-05 status sob demanda', () => {
  it('busca os status das chaves listadas; issue apagada aparece como não encontrada', async () => {
    const { api, user } = setup([issue('ABC-2'), issue('ABC-1')])
    const asked: string[][] = []
    api.issueStatuses = async (keys) => {
      asked.push(keys)
      return { 'ABC-2': { name: 'Em andamento', category: 'indeterminate' }, 'ABC-1': null }
    }
    await screen.findByRole('link', { name: 'ABC-2' })

    await user.click(screen.getByRole('button', { name: 'Refresh Jira status' }))

    expect(await within(row('ABC-2')).findByText('Em andamento')).toBeInTheDocument()
    expect(within(row('ABC-1')).getByText('Not found in Jira')).toBeInTheDocument()
    expect(asked).toEqual([['ABC-2', 'ABC-1']])
  })

  it('token recusado vira um aviso', async () => {
    const { api, user } = setup([issue('ABC-2')])
    api.issueStatuses = async () => {
      throw Object.assign(new Error('x'), { code: 'jira-credential-rejected' })
    }
    await screen.findByRole('link', { name: 'ABC-2' })

    await user.click(screen.getByRole('button', { name: 'Refresh Jira status' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Jira rejected your saved token')
  })
})

describe('F10-RF-06 copiar para agente de código', () => {
  it('copia o texto da spec e avisa', async () => {
    const { api, user } = setup([issue('ABC-2')])
    const writeText = vi.fn(async () => {})
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    api.agentPrompt = async (key) => `Implemente a issue ${key} abaixo.\n\n## Critérios de aceite`

    await user.click(await screen.findByRole('button', { name: 'Copy ABC-2 for a coding agent' }))

    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(
        'Implemente a issue ABC-2 abaixo.\n\n## Critérios de aceite',
      ),
    )
    expect(screen.getByRole('status', { name: '' })).toHaveTextContent('ABC-2 copied')
  })

  it('sem spec guardada, explica o motivo', async () => {
    const { api, user } = setup([issue('ABC-2')])
    api.agentPrompt = async () => {
      throw Object.assign(new Error('x'), { code: 'spec-unavailable' })
    }

    await user.click(await screen.findByRole('button', { name: 'Copy ABC-2 for a coding agent' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('no spec to copy')
  })
})
