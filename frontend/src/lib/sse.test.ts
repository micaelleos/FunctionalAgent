import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { api, server } from '../test/server'
import { ApiError } from './api'
import { type ChatEvent, createSseParser, streamPost } from './sse'

const block = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

function sseResponse(chunks: string[], headers: Record<string, string> = {}) {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
  return new HttpResponse(body, {
    headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-Id': 'c9', ...headers },
  })
}

describe('F08-RT-01 parser de SSE', () => {
  it('junta blocos partidos em qualquer ponto e ignora ping e eventos desconhecidos', () => {
    const events: ChatEvent[] = []
    const parser = createSseParser((e) => events.push(e))
    const text = [
      ': ping\n\n',
      block('token', { text: 'Olá ' }),
      block('futuro', { x: 1 }),
      block('tool_start', { name: 'listar_projetos', summary: 'Checking…' }),
      block('token', { text: 'mundo' }),
    ].join('')

    for (let i = 0; i < text.length; i += 7) parser.push(text.slice(i, i + 7))
    parser.end()

    expect(events).toEqual([
      { event: 'token', text: 'Olá ' },
      { event: 'tool_start', name: 'listar_projetos', summary: 'Checking…' },
      { event: 'token', text: 'mundo' },
    ])
  })

  it('aceita CRLF e o último bloco sem linha em branco', () => {
    const events: ChatEvent[] = []
    const parser = createSseParser((e) => events.push(e))
    parser.push('event: token\r\ndata: {"text":"a"}\r\n\r\nevent: done\r\ndata: {"usage":{}}')
    parser.end()
    expect(events.map((e) => e.event)).toEqual(['token', 'done'])
  })
})

describe('F08-RF-01 POST em streaming', () => {
  it('entrega os eventos em ordem e devolve a conversa do cabeçalho', async () => {
    const seen: { auth: string | null; body: unknown }[] = []
    server.use(
      http.post(api('/api/v1/conversations/new/messages'), async ({ request }) => {
        seen.push({ auth: request.headers.get('Authorization'), body: await request.json() })
        return sseResponse([
          block('token', { text: 'Oi' }),
          block('message_saved', {
            message_id: 'm2',
            conversation_id: 'c9',
            user_message_id: 'm1',
          }),
          block('done', { usage: { input_tokens: 1, output_tokens: 1, cost_usd: 0 } }),
        ])
      }),
    )
    const events: string[] = []

    const result = await streamPost(
      '/api/v1/conversations/new/messages',
      { content: 'Olá' },
      async () => 'token-1',
      (e) => events.push(e.event),
    )

    expect(result).toEqual({ conversationId: 'c9' })
    expect(events).toEqual(['open', 'token', 'message_saved', 'done'])
    expect(seen).toEqual([{ auth: 'Bearer token-1', body: { content: 'Olá' } }])
  })

  it('401 renova o token e tenta de novo antes do stream', async () => {
    const tokens: string[] = []
    server.use(
      http.post(api('/api/v1/conversations/c1/messages'), ({ request }) => {
        const auth = request.headers.get('Authorization') ?? ''
        tokens.push(auth)
        return auth === 'Bearer novo'
          ? sseResponse([block('done', { usage: {} })])
          : HttpResponse.json({ code: 'unauthenticated' }, { status: 401 })
      }),
    )

    await streamPost(
      '/api/v1/conversations/c1/messages',
      { content: 'x' },
      async (force) => (force ? 'novo' : 'velho'),
      () => undefined,
    )

    expect(tokens).toEqual(['Bearer velho', 'Bearer novo'])
  })

  it('erro antes do stream vira ApiError com o código', async () => {
    server.use(
      http.post(api('/api/v1/conversations/x/messages'), () =>
        HttpResponse.json(
          { code: 'conversation-not-found', title: 'Conversa não encontrada' },
          { status: 404 },
        ),
      ),
    )

    const error = await streamPost(
      '/api/v1/conversations/x/messages',
      { content: 'x' },
      async () => 't',
      () => undefined,
    ).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('conversation-not-found')
  })

  it('F08-RF-06 o sinal interrompe a leitura', async () => {
    const controller = new AbortController()
    server.use(
      http.post(api('/api/v1/conversations/c1/messages'), () => {
        const encoder = new TextEncoder()
        const body = new ReadableStream<Uint8Array>({
          start(stream) {
            stream.enqueue(encoder.encode(block('token', { text: 'parcial' })))
            // Não fecha: o servidor ainda estaria gerando.
          },
        })
        return new HttpResponse(body, { headers: { 'Content-Type': 'text/event-stream' } })
      }),
    )
    const events: string[] = []

    const pending = streamPost(
      '/api/v1/conversations/c1/messages',
      { content: 'x' },
      async () => 't',
      (e) => {
        events.push(e.event)
        controller.abort()
      },
      controller.signal,
    )

    await expect(pending).rejects.toThrow()
    expect(events).toEqual(['token'])
  })
})
