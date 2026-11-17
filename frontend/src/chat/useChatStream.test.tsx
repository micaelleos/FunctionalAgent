import { QueryClient, QueryClientProvider, useInfiniteQuery } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { ChatEvent } from '../lib/sse'
import { ProductContext } from '../product/context'
import { createDemoProductApi } from '../product/demo'
import type { ProductApi } from '../product/types'
import { useChatStream } from './useChatStream'

function setup(api: ProductApi, options: Parameters<typeof useChatStream>[0] = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ProductContext.Provider value={api}>{children}</ProductContext.Provider>
    </QueryClientProvider>
  )
  return renderHook(() => useChatStream(options), { wrapper })
}

const script =
  (events: ChatEvent[], conversationId = 'c9'): ProductApi['streamMessage'] =>
  async (_id, _text, onEvent) => {
    for (const e of events) onEvent(e)
    return { conversationId }
  }

describe('F08-RF-01 turno em streaming', () => {
  it('junta os tokens, avisa a conversa nova e limpa o turno no fim', async () => {
    const api = createDemoProductApi(() => 0)
    const seen: string[] = []
    let release: () => void = () => undefined
    api.streamMessage = async (_id, _text, onEvent) => {
      onEvent({ event: 'token', text: 'Olá ' })
      onEvent({ event: 'token', text: 'mundo' })
      onEvent({
        event: 'message_saved',
        message_id: 'm2',
        conversation_id: 'c9',
        user_message_id: 'm1',
      })
      await new Promise<void>((r) => (release = r))
      return { conversationId: 'c9' }
    }
    const { result } = setup(api, { onConversation: (id) => seen.push(id) })

    act(() => void result.current.send(null, 'Oi'))

    await waitFor(() => expect(result.current.turn?.text).toBe('Olá mundo'))
    expect(result.current.busy).toBe(true)
    expect(result.current.turn).toMatchObject({
      conversationId: 'c9',
      messageId: 'm2',
      started: true,
    })
    expect(seen).toEqual(['c9'])
    await act(async () => release())
    // Fica na tela (`done`) até o histórico trazer a resposta `m2`; a página o esconde então.
    await waitFor(() => expect(result.current.turn?.status).toBe('done'))
    expect(result.current.busy).toBe(false)
  })

  it('relê o histórico se a 1ª busca da conversa nova voltou sem a resposta', async () => {
    const api = createDemoProductApi(() => 0)
    const user = { id: 'm1', role: 'user' as const, text: 'Oi', actions: [], interrupted: false }
    const reply = { ...user, id: 'm2', role: 'assistant' as const, text: 'Olá' }
    let finishFirst: () => void = () => undefined
    const getMessages = vi
      .fn<ProductApi['getMessages']>()
      // 1ª busca: começou no `open` e só volta depois do fim do turno, sem a resposta.
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishFirst = () => resolve({ items: [user], nextCursor: null })
          }),
      )
      .mockResolvedValue({ items: [user, reply], nextCursor: null })
    api.getMessages = getMessages
    api.streamMessage = async (_id, _text, onEvent) => {
      onEvent({ event: 'open', conversation_id: 'c9' })
      // A página já pediu o histórico da conversa nova; a busca está em andamento.
      while (getMessages.mock.calls.length === 0) await new Promise((r) => setTimeout(r, 5))
      onEvent({ event: 'token', text: 'Olá' })
      onEvent({
        event: 'message_saved',
        message_id: 'm2',
        conversation_id: 'c9',
        user_message_id: 'm1',
      })
      setTimeout(() => finishFirst(), 20)
      return { conversationId: 'c9' }
    }
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>
        <ProductContext.Provider value={api}>{children}</ProductContext.Provider>
      </QueryClientProvider>
    )
    const { result } = renderHook(
      () => {
        const stream = useChatStream()
        const id = stream.turn?.conversationId ?? null
        const history = useInfiniteQuery({
          queryKey: ['messages', id],
          queryFn: ({ pageParam }) => api.getMessages(id ?? '', pageParam),
          initialPageParam: null as string | null,
          getNextPageParam: (page) => page.nextCursor,
          enabled: id !== null,
        })
        return { stream, ids: history.data?.pages.flatMap((p) => p.items.map((m) => m.id)) }
      },
      { wrapper },
    )

    act(() => void result.current.stream.send(null, 'Oi'))

    await waitFor(() => expect(result.current.ids).toEqual(['m1', 'm2']))
    expect(getMessages.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(result.current.stream.turn).toMatchObject({ status: 'done', messageId: 'm2' })
  })

  it('não envia dois turnos ao mesmo tempo', async () => {
    const api = createDemoProductApi(() => 0)
    const send = vi.fn<ProductApi['streamMessage']>(() => new Promise(() => undefined))
    api.streamMessage = send
    const { result } = setup(api)

    act(() => {
      void result.current.send('c1', 'a')
      void result.current.send('c1', 'b')
    })

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  })
})

describe('F08-RF-06 parar', () => {
  it('aborta o sinal e marca o turno como parado', async () => {
    const api = createDemoProductApi(() => 0)
    let signal: AbortSignal | undefined
    api.streamMessage = (_id, _t, onEvent, s) => {
      signal = s
      onEvent({ event: 'token', text: 'parcial' })
      return new Promise((_r, reject) =>
        s?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
      )
    }
    const { result } = setup(api)

    act(() => void result.current.send('c1', 'Explique'))
    await waitFor(() => expect(result.current.turn?.started).toBe(true))
    act(() => result.current.stop())

    await waitFor(() => expect(result.current.turn?.status).toBe('stopped'))
    expect(signal?.aborted).toBe(true)
    expect(result.current.turn?.text).toBe('parcial')
    expect(result.current.busy).toBe(false)
  })
})

describe('F08-RF-06 parar numa conversa nova', () => {
  it('a conversa do cabeçalho (open) chega antes do fim e não se perde ao parar', async () => {
    const api = createDemoProductApi(() => 0)
    api.streamMessage = (_id, _t, onEvent, s) => {
      onEvent({ event: 'open', conversation_id: 'c7' })
      onEvent({ event: 'token', text: 'parcial' })
      return new Promise((_r, reject) =>
        s?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
      )
    }
    const seen: string[] = []
    const { result } = setup(api, { onConversation: (id) => seen.push(id) })

    act(() => void result.current.send(null, 'Explique'))
    await waitFor(() => expect(seen).toEqual(['c7']))
    act(() => result.current.stop())

    await waitFor(() => expect(result.current.turn?.status).toBe('stopped'))
    expect(result.current.turn?.conversationId).toBe('c7')
  })
})

describe('F08-RF-07 falhas', () => {
  it('sem rede antes de começar: devolve o texto ao campo', async () => {
    const api = createDemoProductApi(() => 0)
    api.streamMessage = () => Promise.reject(new TypeError('Failed to fetch'))
    const restored: string[] = []
    const { result } = setup(api, { onRestore: (t) => restored.push(t) })

    await act(() => result.current.send('c1', 'Olá'))

    expect(result.current.turn).toMatchObject({ status: 'failed', error: { code: 'network' } })
    expect(restored).toEqual(['Olá'])
  })

  it('erro do agente no meio: fica na tela e "retry" reenvia o mesmo texto', async () => {
    const api = createDemoProductApi(() => 0)
    const send = vi
      .fn<ProductApi['streamMessage']>()
      .mockImplementationOnce(
        script(
          [
            { event: 'token', text: 'Vou' },
            { event: 'error', code: 'turn-timeout', message: 'Demorou' },
          ],
          'c1',
        ),
      )
      .mockImplementationOnce(script([{ event: 'token', text: 'ok' }]))
    api.streamMessage = send
    const restored: string[] = []
    const { result } = setup(api, { onRestore: (t) => restored.push(t) })

    await act(() => result.current.send('c1', 'Crie'))
    expect(result.current.turn).toMatchObject({ status: 'failed', error: { code: 'turn-timeout' } })
    expect(restored).toEqual([])

    await act(async () => result.current.retry())
    await waitFor(() => expect(send).toHaveBeenCalledTimes(2))
    expect(send.mock.calls[1].slice(0, 2)).toEqual(['c1', 'Crie'])
  })
})
