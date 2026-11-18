import { API_BASE_URL, ApiError, type TokenGetter, toApiError } from './api'
import { withAppCheck } from './appCheck'

/**
 * Eventos do chat (docs/api/sse-events.v1.json, F05-RT-02). `open` é só do cliente: o stream
 * começou e o cabeçalho `X-Conversation-Id` já diz a conversa (criada pelo envio para `new`).
 */
export type ChatEvent =
  | { event: 'open'; conversation_id: string }
  | { event: 'token'; text: string }
  | { event: 'tool_start'; name: string; summary: string }
  | { event: 'tool_end'; name: string; summary: string }
  | {
      event: 'action_proposed'
      action_id: string
      kind: 'create_issue' | 'update_issue'
      preview: Record<string, unknown>
    }
  | { event: 'message_saved'; message_id: string; conversation_id: string; user_message_id: string }
  | { event: 'error'; code: string; message: string }
  | { event: 'done'; usage: { input_tokens: number; output_tokens: number; cost_usd: number } }

const KNOWN = new Set([
  'token',
  'tool_start',
  'tool_end',
  'action_proposed',
  'message_saved',
  'error',
  'done',
])

/**
 * Lê `text/event-stream` em blocos separados por linha em branco (`event:` + `data:`). Os
 * pedaços da rede podem cortar um bloco em qualquer ponto; o resto fica no buffer. Comentários
 * (`: ping`) e eventos desconhecidos são ignorados (versões novas do servidor não quebram o front).
 */
export function createSseParser(onEvent: (event: ChatEvent) => void) {
  let buffer = ''
  const flush = (block: string) => {
    let name = 'message'
    const data: string[] = []
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) name = line.slice(6).trim()
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''))
    }
    if (!KNOWN.has(name) || data.length === 0) return
    const payload = JSON.parse(data.join('\n')) as Record<string, unknown>
    onEvent({ ...payload, event: name } as ChatEvent)
  }
  return {
    push(chunk: string) {
      buffer += chunk.replace(/\r\n?/g, '\n')
      let end = buffer.indexOf('\n\n')
      while (end !== -1) {
        flush(buffer.slice(0, end))
        buffer = buffer.slice(end + 2)
        end = buffer.indexOf('\n\n')
      }
    },
    end() {
      if (buffer.trim()) flush(buffer)
      buffer = ''
    },
  }
}

export interface StreamResult {
  /** `X-Conversation-Id`: a conversa criada quando o envio foi para `new`. */
  conversationId: string
}

/**
 * POST que responde em SSE (F08-RT-01). Erros antes do stream (404, 422, 401 depois de renovar o
 * token) viram `ApiError`, como no resto da API; `signal` cancela a leitura ("Parar").
 */
export async function streamPost(
  path: string,
  body: unknown,
  getToken: TokenGetter,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<StreamResult> {
  const send = async (forceRefresh: boolean) => {
    const headers = await withAppCheck(
      new Headers({ 'Content-Type': 'application/json', Accept: 'text/event-stream' }),
    )
    const token = await getToken(forceRefresh)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    return fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    })
  }
  let response = await send(false)
  if (response.status === 401) response = await send(true)
  if (!response.ok) throw await toApiError(response)
  if (!response.body) throw new ApiError(0, 'stream-unsupported', 'Streaming not supported')
  const conversationId = response.headers.get('X-Conversation-Id') ?? ''
  if (conversationId) onEvent({ event: 'open', conversation_id: conversationId })

  const parser = createSseParser(onEvent)
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  // Cancelar o leitor encerra a leitura em qualquer ambiente (o fetch também aborta o corpo).
  const cancel = () => void reader.cancel().catch(() => undefined)
  signal?.addEventListener('abort', cancel)
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      if (done) break
      parser.push(value)
    }
    parser.end()
  } finally {
    signal?.removeEventListener('abort', cancel)
    reader.releaseLock()
  }
  return { conversationId }
}
