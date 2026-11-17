import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { api, server } from '../test/server'
import { createHttpProductApi } from './http'

const conversation = {
  id: 'c1',
  title: 'Checkout',
  project_key: 'SCRUM',
  created_at: '2026-11-17T10:00:00Z',
  updated_at: '2026-11-17T11:00:00Z',
  message_count: 2,
}

const product = () => createHttpProductApi(async () => 'token-1')

describe('F08-RF-05 conversas pela API da F07', () => {
  it('lista as mais recentes', async () => {
    const urls: string[] = []
    server.use(
      http.get(api('/api/v1/conversations'), ({ request }) => {
        urls.push(new URL(request.url).search)
        return HttpResponse.json({ items: [conversation], next_cursor: null })
      }),
    )

    expect(await product().listConversations()).toEqual([
      { id: 'c1', title: 'Checkout', projectKey: 'SCRUM', updatedAt: '2026-11-17T11:00:00Z' },
    ])
    expect(urls).toEqual(['?limit=50'])
  })

  it('criar, renomear, fixar/soltar e excluir mandam só o que muda', async () => {
    const calls: { method: string; path: string; body: unknown }[] = []
    const record = async ({ request }: { request: Request }) => {
      const body = request.method === 'DELETE' ? null : await request.json()
      calls.push({ method: request.method, path: new URL(request.url).pathname, body })
      return request.method === 'DELETE'
        ? new HttpResponse(null, { status: 204 })
        : HttpResponse.json(conversation, { status: request.method === 'POST' ? 201 : 200 })
    }
    server.use(
      http.post(api('/api/v1/conversations'), record),
      http.patch(api('/api/v1/conversations/c1'), record),
      http.delete(api('/api/v1/conversations/c1'), record),
    )
    const p = product()

    await p.createConversation('SCRUM')
    await p.renameConversation('c1', 'Checkout v2')
    await p.pinProject('c1', null)
    await p.deleteConversation('c1')

    expect(calls).toEqual([
      { method: 'POST', path: '/api/v1/conversations', body: { project_key: 'SCRUM' } },
      { method: 'PATCH', path: '/api/v1/conversations/c1', body: { title: 'Checkout v2' } },
      { method: 'PATCH', path: '/api/v1/conversations/c1', body: { project_key: null } },
      { method: 'DELETE', path: '/api/v1/conversations/c1', body: null },
    ])
  })
})

describe('F08-RF-03 histórico com cartões', () => {
  it('mapeia mensagens, ações e o cursor', async () => {
    const searches: string[] = []
    server.use(
      http.get(api('/api/v1/conversations/c1/messages'), ({ request }) => {
        searches.push(new URL(request.url).search)
        return HttpResponse.json({
          items: [
            {
              id: 'm2',
              role: 'assistant',
              text: 'Proposta pronta.',
              created_at: '2026-11-17T11:00:00Z',
              interrupted: true,
              actions: [
                {
                  id: 'a1',
                  kind: 'create_issue',
                  status: 'done',
                  conversation_id: 'c1',
                  preview: { project_key: 'SCRUM', issue_type: 'Task', summary: 'Revisar' },
                  readiness: { ready: true, rules: [] },
                  labels: ['specflow'],
                  created_at: '2026-11-17T11:00:00Z',
                  expires_at: '2026-11-18T11:00:00Z',
                  result: { issue_key: 'SCRUM-9', url: 'https://x/browse/SCRUM-9' },
                },
              ],
            },
          ],
          next_cursor: 'abc',
        })
      }),
    )

    const page = await product().getMessages('c1', 'cur+1')

    expect(searches).toEqual(['?limit=50&cursor=cur%2B1'])
    expect(page.nextCursor).toBe('abc')
    const [message] = page.items
    expect([message.role, message.text, message.interrupted]).toEqual([
      'assistant',
      'Proposta pronta.',
      true,
    ])
    expect([message.actions[0].status, message.actions[0].resultKey]).toEqual(['done', 'SCRUM-9'])
  })

  it('o chat fica ligado na produção', () => {
    expect(product().features.chat).toBe(true)
  })
})
