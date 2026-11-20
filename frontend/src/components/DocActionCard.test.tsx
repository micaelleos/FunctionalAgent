import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ActionProblem, fromApiAction, type ApiAction } from '../product/actions'
import { ProductContext } from '../product/context'
import type { ProductApi, ProposedAction } from '../product/types'
import { unavailableProductApi } from '../product/unavailable'
import { ActionCard } from './ActionCard'

const SPACE = {
  key: 'SCRUM',
  name: 'Minha equipe',
  url: 'https://demo.atlassian.net/wiki/spaces/SCRUM',
}

function apiAction(kind: ApiAction['kind'], preview: Record<string, unknown>): ApiAction {
  return {
    id: 'd1',
    kind,
    status: 'pending',
    conversation_id: 'c1',
    preview,
    readiness: {},
    labels: [],
    created_at: '2026-11-20T12:00:00Z',
    expires_at: '2026-11-21T12:00:00Z',
  }
}

const update = fromApiAction(
  apiAction('update_page', {
    title: 'Glossário',
    page_type: 'glossario',
    summary: 'Termo Cliente',
    space: SPACE,
    url: 'https://demo.atlassian.net/wiki/spaces/SCRUM/pages/901',
    version: 3,
    diff: [
      {
        section: 'Termos',
        change: 'changed',
        before: 'Pedido: compra',
        after: 'Pedido: compra **confirmada**',
      },
      { section: 'Novos', change: 'added', before: '', after: 'Cliente' },
    ],
  }),
)

function renderCard(action: ProposedAction, api: Partial<ProductApi> = {}) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <ProductContext.Provider value={{ ...unavailableProductApi, ...api }}>
        <ActionCard action={action} conversationId="c1" />
      </ProductContext.Provider>
    </QueryClientProvider>,
  )
}

describe('F20-RF-03 proposta de atualização com o diff por seção', () => {
  it('mostra a versão vista, o resumo e o antes → depois de cada seção', () => {
    renderCard(update)
    const card = screen.getByRole('region', { name: 'Update page “Glossário”' })
    expect(card).toHaveTextContent('Based on version 3')
    expect(card).toHaveTextContent('Termo Cliente')
    expect(within(card).getByRole('link', { name: 'Open the current page' })).toHaveAttribute(
      'href',
      'https://demo.atlassian.net/wiki/spaces/SCRUM/pages/901',
    )
    const terms = within(card).getByRole('region', { name: 'Termos' })
    expect(within(terms).getByLabelText('Before')).toHaveTextContent('Pedido: compra')
    expect(within(terms).getByLabelText('After')).toHaveTextContent('Pedido: compra confirmada')
    expect(within(card).getByRole('region', { name: 'Novos' })).toHaveTextContent('new')
  })
})

describe('F20-RF-04 página editada depois da proposta', () => {
  it('a confirmação falha com a mensagem do conflito e nada é sobrescrito', async () => {
    const failed: ProposedAction = {
      ...update,
      status: 'failed',
      error: 'A página mudou no Confluence depois da proposta.',
      errorCode: 'confluence-version-conflict',
    }
    const confirmAction = vi
      .fn()
      .mockRejectedValue(new ActionProblem('confluence-version-conflict', 'x', failed))
    renderCard(update, { confirmAction })

    await userEvent.click(screen.getByRole('button', { name: 'Confirm and write' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'This page changed since the proposal. Ask the agent to review it again.',
    )
    expect(screen.queryByRole('button', { name: 'Confirm and write' })).not.toBeInTheDocument()
  })
})

describe('F20-RT-01 nada é escrito sem Confirm', () => {
  it('Discard não confirma e diz que nada foi escrito', async () => {
    const confirmAction = vi.fn()
    const rejectAction = vi.fn().mockResolvedValue({ ...update, status: 'rejected' })
    renderCard(update, { confirmAction, rejectAction })

    await userEvent.click(screen.getByRole('button', { name: 'Discard' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Discarded. Nothing was written to Confluence.',
    )
    expect(confirmAction).not.toHaveBeenCalled()
  })
})

describe('F20-RF-02 F20-RF-01 página nova e espaço', () => {
  it('página nova mostra onde entra e o conteúdo; confirmada, o link e o aviso', async () => {
    const create = fromApiAction(
      apiAction('create_page', {
        title: 'ADR-002 — Fila',
        page_type: 'adr',
        summary: 'Decisão da fila',
        space: SPACE,
        parent_title: 'Decisões (ADR)',
        diff: [{ section: 'Decisão', change: 'added', before: '', after: 'Usar Pub/Sub.' }],
      }),
    )
    const confirmAction = vi.fn().mockResolvedValue({
      ...create,
      status: 'done',
      resultUrl: 'https://demo.atlassian.net/wiki/spaces/SCRUM/pages/950',
      warning: 'A página foi escrita, mas o Registro de mudanças não foi atualizado.',
    })
    renderCard(create, { confirmAction })

    const card = screen.getByRole('region', { name: 'Create page “ADR-002 — Fila”' })
    expect(card).toHaveTextContent('Decision (ADR)')
    expect(card).toHaveTextContent('Decisões (ADR)')
    expect(card).toHaveTextContent('Usar Pub/Sub.')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm and write' }))
    expect(await screen.findByRole('link', { name: 'Open in Confluence' })).toHaveAttribute(
      'href',
      'https://demo.atlassian.net/wiki/spaces/SCRUM/pages/950',
    )
    expect(screen.getByRole('status')).toHaveTextContent('Registro de mudanças não foi atualizado')
  })

  it('espaço lista as páginas do modelo', () => {
    renderCard(
      fromApiAction(
        apiAction('create_space', {
          title: 'Scrum — Documentação',
          space_key: 'SCRUM',
          project_key: 'SCRUM',
          pages: ['Início', 'Constituição', 'Registro de mudanças'],
        }),
      ),
    )
    const card = screen.getByRole('region', { name: 'Create space “Scrum — Documentação”' })
    expect(
      within(card)
        .getAllByRole('listitem')
        .map((li) => li.textContent),
    ).toEqual(['Início', 'Constituição', 'Registro de mudanças'])
    expect(within(card).getByRole('button', { name: 'Confirm and create space' })).toBeEnabled()
  })
})
