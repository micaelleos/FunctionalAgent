import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ActionProblem } from '../product/actions'
import { ProductContext } from '../product/context'
import type { ProductApi, ProposedAction } from '../product/types'
import { unavailableProductApi } from '../product/unavailable'
import { ActionCard } from './ActionCard'

const base: ProposedAction = {
  id: 'a1',
  kind: 'create_issue',
  projectKey: 'SCRUM',
  projectName: 'Sandbox',
  issueKey: null,
  issueType: 'Story',
  title: 'Filtrar Meus pedidos por período',
  priority: null,
  parentKey: null,
  labels: ['agent-ready', 'specflow'],
  sections: [
    { title: 'Objetivo', markdown: 'Como cliente, quero filtrar por **período**.' },
    {
      title: 'Critérios de aceite',
      markdown: '**CA-01 (erro) Datas invertidas**\nDado a tela aberta\nEntão vejo `erro`',
    },
    { title: 'Fora de escopo', markdown: '- Exportar pedidos.\n- Busca por texto.' },
    { title: 'Como verificar', markdown: '- Unidade e E2E do filtro.' },
  ],
  readiness: { ready: true, rules: [] },
  conflicts: [],
  changes: [],
  expiresAt: '2026-11-17T12:00:00Z',
  status: 'pending',
  resultKey: null,
  resultUrl: null,
  error: null,
}

function renderCard(action: Partial<ProposedAction> = {}, api: Partial<ProductApi> = {}) {
  const product = { ...unavailableProductApi, ...api }
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <ProductContext.Provider value={product}>
        <ActionCard action={{ ...base, ...action }} conversationId="c1" />
      </ProductContext.Provider>
    </QueryClientProvider>,
  )
  return product
}

describe('F06-RF-01 cartão com a spec por seção', () => {
  it('mostra projeto, tipo, prioridade, labels e cada seção', () => {
    renderCard()
    const card = screen.getByRole('region', { name: 'Create Story in SCRUM' })

    expect(within(card).getByText('SCRUM · Sandbox')).toBeInTheDocument()
    expect(within(card).getByText('Project default')).toBeInTheDocument()
    expect(within(card).getByText('agent-ready, specflow')).toBeInTheDocument()
    for (const title of ['Objetivo', 'Critérios de aceite', 'Fora de escopo', 'Como verificar']) {
      expect(within(card).getByRole('region', { name: title })).toBeInTheDocument()
    }
    expect(within(card).getByText('período').tagName).toBe('STRONG')
    expect(within(card).getByText('Exportar pedidos.').tagName).toBe('LI')
  })

  it('texto do agente não vira HTML', () => {
    renderCard({ sections: [{ title: 'Objetivo', markdown: '<img src=x onerror=alert(1)>' }] })
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })
})

describe('F06-RF-08 prontidão no cartão', () => {
  it('pronta para agente', () => {
    renderCard()
    expect(screen.getByRole('group', { name: 'Readiness for a coding agent' })).toHaveTextContent(
      'Ready for a coding agent',
    )
  })

  it('lista o que falta e ainda deixa confirmar', () => {
    renderCard({
      labels: ['specflow'],
      readiness: {
        ready: false,
        rules: [
          {
            id: 'P-04',
            label: 'Cenário de erro ou de borda',
            severity: 'obrigatória',
            passed: false,
            detail: '',
          },
          {
            id: 'P-08',
            label: 'Sem termos vagos',
            severity: 'aviso',
            passed: false,
            detail: 'rápido',
          },
        ],
      },
    })
    const box = screen.getByRole('group', { name: 'Readiness for a coding agent' })

    expect(box).toHaveTextContent('Missing: Cenário de erro ou de borda (P-04)')
    expect(box).toHaveTextContent('Warning: Sem termos vagos (P-08) — rápido')
    expect(screen.getByRole('button', { name: 'Confirm and create' })).toBeEnabled()
  })
})

describe('F06-RF-06 atualização com antes e depois', () => {
  it('mostra o valor atual riscado e o novo', () => {
    renderCard({
      kind: 'update_issue',
      projectKey: null,
      issueKey: 'SCRUM-1',
      changes: [{ field: 'summary', before: 'Login', after: 'Login com e-mail' }],
    })
    const card = screen.getByRole('region', { name: 'Update SCRUM-1' })

    expect(within(card).getByText('Login').tagName).toBe('DEL')
    expect(within(card).getByText('Login com e-mail').tagName).toBe('INS')
    expect(within(card).getByRole('button', { name: 'Confirm and update' })).toBeInTheDocument()
  })
})

describe('F06-RF-02 confirmar e recusar', () => {
  it('confirmar mostra a chave e o link', async () => {
    const confirmAction = vi.fn().mockResolvedValue({
      ...base,
      status: 'done',
      resultKey: 'SCRUM-12',
      resultUrl: 'https://sandbox.atlassian.net/browse/SCRUM-12',
    })
    renderCard({}, { confirmAction })

    await userEvent.click(screen.getByRole('button', { name: 'Confirm and create' }))

    expect(confirmAction).toHaveBeenCalledWith('a1', expect.anything())
    expect(await screen.findByRole('status')).toHaveTextContent('Created as SCRUM-12')
    expect(screen.getByRole('link', { name: 'Open in Jira' })).toHaveAttribute(
      'href',
      'https://sandbox.atlassian.net/browse/SCRUM-12',
    )
    expect(screen.queryByRole('button', { name: 'Confirm and create' })).not.toBeInTheDocument()
  })

  it('F06-RF-03 recusar não envia nada e mostra Recusada', async () => {
    const confirmAction = vi.fn()
    const rejectAction = vi.fn().mockResolvedValue({ ...base, status: 'rejected' })
    renderCard({}, { confirmAction, rejectAction })

    await userEvent.click(screen.getByRole('button', { name: 'Reject' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Nothing was sent to Jira')
    expect(confirmAction).not.toHaveBeenCalled()
  })

  it('F06-RF-07 erro do Jira traduzido vira estado de falha', async () => {
    const message = 'Você não tem permissão para criar issues no projeto SCRUM.'
    const failed = { ...base, status: 'failed' as const, error: message }
    const confirmAction = vi
      .fn()
      .mockRejectedValue(new ActionProblem('jira-forbidden', message, failed))
    renderCard({}, { confirmAction })

    await userEvent.click(screen.getByRole('button', { name: 'Confirm and create' }))

    expect(await screen.findByRole('status')).toHaveTextContent(message)
    expect(screen.getByRole('status')).toHaveTextContent('Ask the agent to adjust the proposal.')
    expect(screen.queryByRole('button', { name: 'Confirm and create' })).not.toBeInTheDocument()
  })

  it('erro em que o Jira não gravou mantém o cartão pendente com o aviso', async () => {
    const message = 'O Jira está limitando as requisições. Confirme de novo em alguns minutos.'
    const pending = { ...base, error: message }
    const confirmAction = vi
      .fn()
      .mockRejectedValue(new ActionProblem('jira-rate-limited', message, pending))
    renderCard({}, { confirmAction })

    await userEvent.click(screen.getByRole('button', { name: 'Confirm and create' }))

    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm and create' })).toBeEnabled()
  })

  it('F06-RF-05 expirada não tem botões', () => {
    renderCard({ status: 'expired' })
    expect(screen.getByRole('status')).toHaveTextContent('Expired without confirmation')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('F19-RF-07 conflito com a documentação do projeto', () => {
  it('mostra cada conflito com o ID e o motivo', () => {
    renderCard({ conflicts: [{ id: 'RN-03', reason: 'aprova pedidos de qualquer valor' }] })
    const box = screen.getByRole('group', { name: 'Conflicts with the project documentation' })
    expect(box).toHaveTextContent('Conflicts with RN-03: aprova pedidos de qualquer valor')
  })

  it('sem conflito, nada aparece', () => {
    renderCard()
    expect(
      screen.queryByRole('group', { name: 'Conflicts with the project documentation' }),
    ).not.toBeInTheDocument()
  })
})
