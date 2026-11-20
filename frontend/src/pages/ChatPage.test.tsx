import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { STOP_REFRESH_MS } from '../chat/useChatStream'
import type { ChatEvent } from '../lib/sse'
import { ApiError } from '../lib/api'
import { createDemoProductApi } from '../product/demo'
import type { ProductApi } from '../product/types'
import { ALICE, fakeAuth } from '../test/fakeAuth'

afterEach(() => vi.restoreAllMocks())

const NOW = Date.parse('2026-11-17T12:00:00Z')

function renderApp(path: string, productApi: ProductApi) {
  render(<App authClient={fakeAuth(ALICE).client} productApi={productApi} initialPath={path} />)
}

/** Streaming controlado pelo teste: cada `emit` entrega um evento; `finish` encerra. */
function controlledStream(api: ProductApi) {
  let emit: (e: ChatEvent) => void = () => undefined
  let finish: () => void = () => undefined
  let signal: AbortSignal | undefined
  const calls: { conversationId: string | null; text: string }[] = []
  api.streamMessage = vi.fn(async (conversationId, text, onEvent, s) => {
    calls.push({ conversationId, text })
    emit = onEvent
    signal = s
    await new Promise<void>((resolve, reject) => {
      finish = resolve
      s?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })
    return { conversationId: conversationId ?? 'c1' }
  })
  return {
    calls,
    emit: (e: ChatEvent) => act(() => emit(e)),
    finish: () => act(async () => finish()),
    aborted: () => signal?.aborted ?? false,
  }
}

async function typeAndSend(text: string) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Message'), `${text}{Enter}`)
  return user
}

describe('F08-RF-01 resposta em streaming', () => {
  it('o texto cresce aos poucos e a mensagem do usuário aparece na hora', async () => {
    const api = createDemoProductApi(() => NOW)
    const stream = controlledStream(api)
    renderApp('/chat/c1', api)

    await typeAndSend('Liste critérios')
    expect(screen.getAllByText('Liste critérios').length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Message')).toHaveValue('')

    await stream.emit({ event: 'token', text: 'Primeiro ' })
    expect(await screen.findByText(/Primeiro/)).toBeInTheDocument()
    await stream.emit({ event: 'token', text: '**critério**' })
    expect(await screen.findByText('critério')).toHaveProperty('tagName', 'STRONG')
    expect(stream.calls).toEqual([{ conversationId: 'c1', text: 'Liste critérios' }])
    await stream.finish()
  })
})

describe('F08-RF-03 F08-RF-04 ferramenta e cartão no fluxo', () => {
  it('mostra a ferramenta em uso e o cartão proposto durante o turno', async () => {
    const api = createDemoProductApi(() => NOW)
    const stream = controlledStream(api)
    renderApp('/chat/c1', api)
    await typeAndSend('Crie a task')

    await stream.emit({
      event: 'tool_start',
      name: 'listar_projetos',
      summary: 'Checking Jira projects…',
    })
    expect(await screen.findByText('Checking Jira projects…')).toBeInTheDocument()
    await stream.emit({ event: 'tool_end', name: 'listar_projetos', summary: 'Done' })
    await stream.emit({
      event: 'action_proposed',
      action_id: 'a9',
      kind: 'create_issue',
      preview: {
        project_key: 'SCRUM',
        project_name: 'Sandbox',
        issue_type: 'Task',
        summary: 'Revisar textos',
        sections: [{ title: 'Objetivo', markdown: 'Revisar.' }],
        readiness: { ready: true, rules: [] },
        labels: ['specflow'],
      },
    })

    const card = await screen.findByRole('region', { name: 'Create Task in SCRUM' })
    expect(within(card).getByRole('button', { name: 'Confirm and create' })).toBeEnabled()
    expect(within(card).getByRole('button', { name: 'Reject' })).toBeEnabled()
    expect(screen.queryByText('Checking Jira projects…')).not.toBeInTheDocument()
    await stream.finish()
  })
})

describe('F08-RF-06 parar', () => {
  it('"Stop" interrompe e marca a resposta parcial', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const api = createDemoProductApi(() => NOW)
    const stream = controlledStream(api)
    renderApp('/chat/c1', api)
    const user = await typeAndSend('Explique tudo')

    await stream.emit({ event: 'token', text: 'Começo da resposta' })
    await user.click(await screen.findByRole('button', { name: 'Stop' }))

    expect(stream.aborted()).toBe(true)
    expect(await screen.findByText('Interrupted: you stopped this answer.')).toBeInTheDocument()
    expect(screen.getByText('Começo da resposta')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
    await act(async () => {
      vi.advanceTimersByTime(STOP_REFRESH_MS + 10)
    })
    vi.useRealTimers()
  })

  it('o histórico mostra a resposta interrompida', async () => {
    const api = createDemoProductApi(() => NOW)
    api.getMessages = async () => ({
      items: [
        { id: 'u', role: 'user', text: 'Explique', actions: [], interrupted: false },
        { id: 'a', role: 'assistant', text: 'Parcial', actions: [], interrupted: true },
      ],
      nextCursor: null,
    })
    renderApp('/chat/c1', api)

    expect(await screen.findByText('Parcial')).toBeInTheDocument()
    expect(screen.getByText('Interrupted: you stopped this answer.')).toBeInTheDocument()
  })
})

describe('F08-RF-07 erros', () => {
  it('sem rede: aviso, o texto volta ao campo e "Try again" reenvia', async () => {
    const api = createDemoProductApi(() => NOW)
    const send = vi
      .fn<ProductApi['streamMessage']>()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({ conversationId: 'c1' })
    api.streamMessage = send
    renderApp('/chat/c1', api)
    const user = await typeAndSend('Olá')

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't reach the server")
    expect(screen.getByLabelText('Message')).toHaveValue('Olá')
    await user.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(send).toHaveBeenCalledTimes(2))
    expect(send.mock.calls[1].slice(0, 2)).toEqual(['c1', 'Olá'])
  })

  it('erro do agente no meio: mensagem traduzida e "Try again"', async () => {
    const api = createDemoProductApi(() => NOW)
    const stream = controlledStream(api)
    renderApp('/chat/c1', api)
    const user = await typeAndSend('Crie')

    await stream.emit({ event: 'token', text: 'Vou ' })
    await stream.emit({
      event: 'error',
      code: 'llm-unavailable',
      message: 'O modelo está indisponível',
    })
    await stream.finish()

    expect(await screen.findByRole('alert')).toHaveTextContent('The model is unavailable right now')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(stream.calls).toHaveLength(2))
    expect(stream.calls[1].text).toBe('Crie')
    await stream.finish()
  })

  it('erro da API antes do stream mostra o código traduzido', async () => {
    const api = createDemoProductApi(() => NOW)
    api.streamMessage = vi
      .fn()
      .mockRejectedValue(new ApiError(404, 'conversation-not-found', 'Conversa não encontrada'))
    renderApp('/chat/c1', api)
    await typeAndSend('Oi')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This conversation no longer exists.',
    )
  })
})

describe('F12-RF-05 teto mensal do beta no chat', () => {
  it('mensagem do teto mensal, sem "Try again", texto de volta ao campo', async () => {
    const api = createDemoProductApi(() => NOW)
    api.streamMessage = vi.fn().mockRejectedValue(
      new ApiError(429, 'beta-budget-exhausted', 'Limite mensal do beta atingido', {
        code: 'beta-budget-exhausted',
        resets_at: '2026-12-01T03:00:00+00:00',
      }),
    )
    renderApp('/chat/c1', api)
    await typeAndSend('Oi')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      "The beta has used this month's usage limit. Chat is back on the 1st (Brasília time).",
    )
    expect(within(alert).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toHaveValue('Oi')
  })
})

describe('F11-RF-02 F11-RF-03 limites de uso no chat', () => {
  it('cota do dia: mensagem com a renovação, sem "Try again", e o uso é relido', async () => {
    const api = createDemoProductApi(() => NOW)
    const getUsage = vi.spyOn(api, 'getUsage')
    api.streamMessage = vi.fn().mockRejectedValue(
      new ApiError(429, 'quota-exceeded', 'Limite diário atingido', {
        code: 'quota-exceeded',
        resets_at: '2026-11-18T03:00:00+00:00',
      }),
    )
    renderApp('/chat/c1', api)
    await waitFor(() => expect(getUsage).toHaveBeenCalled())
    const before = getUsage.mock.calls.length
    await typeAndSend('Oi')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      "You've reached today's limit. It renews at 00:00 (Brasília time).",
    )
    expect(within(alert).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toHaveValue('Oi')
    await waitFor(() => expect(getUsage.mock.calls.length).toBeGreaterThan(before))
  })

  it('rate limit: diz quantos segundos esperar e deixa tentar de novo', async () => {
    const api = createDemoProductApi(() => NOW)
    api.streamMessage = vi.fn().mockRejectedValue(
      new ApiError(429, 'rate-limited', 'Muitas mensagens', {
        code: 'rate-limited',
        retry_after: 42,
      }),
    )
    renderApp('/chat/c1', api)
    await typeAndSend('Oi')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Too many messages. Wait 42 seconds and try again.')
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('F08-RF-01 histórico paginado e conversa nova', () => {
  it('"Load earlier messages" traz a página anterior em cima', async () => {
    const api = createDemoProductApi(() => NOW)
    api.getMessages = async (_id, cursor) =>
      cursor
        ? {
            items: [
              { id: 'old', role: 'user', text: 'Mensagem antiga', actions: [], interrupted: false },
            ],
            nextCursor: null,
          }
        : {
            items: [
              {
                id: 'new',
                role: 'user',
                text: 'Mensagem recente',
                actions: [],
                interrupted: false,
              },
            ],
            nextCursor: 'cur-1',
          }
    renderApp('/chat/c1', api)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Load earlier messages' }))

    const old = await screen.findByText('Mensagem antiga')
    const recent = screen.getByText('Mensagem recente')
    expect(old.compareDocumentPosition(recent) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Load earlier messages' })).not.toBeInTheDocument()
  })

  it('com projeto em ?projeto=, a conversa nasce com ele fixado', async () => {
    const api = createDemoProductApi(() => NOW)
    const create = vi.spyOn(api, 'createConversation')
    const send = vi.spyOn(api, 'streamMessage')
    renderApp('/chat?projeto=SCRUM', api)

    expect(await screen.findByText('Pinned project: SCRUM')).toBeInTheDocument()
    await typeAndSend('Crie uma task')

    await waitFor(() => expect(send).toHaveBeenCalled())
    expect(create).toHaveBeenCalledWith('SCRUM')
    const created = await create.mock.results[0].value
    expect(send.mock.calls[0][0]).toBe(created.id)
  })
})
