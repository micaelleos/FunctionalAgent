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

describe('F09-RF-01 F09-RF-07 projetos pela API', () => {
  it('mapeia os projetos e "refresh" ignora o cache', async () => {
    const searches: string[] = []
    server.use(
      http.get(api('/api/v1/jira/projects'), ({ request }) => {
        searches.push(new URL(request.url).search)
        return HttpResponse.json({
          items: [
            {
              id: '1',
              key: 'SCRUM',
              name: 'Sandbox',
              type: 'software',
              avatar_url: null,
              open_issues: null,
              total_issues: 22,
              url: 'https://x.atlassian.net/browse/SCRUM',
            },
          ],
          fetched_at: '2026-11-17T12:00:00Z',
        })
      }),
    )
    const p = product()

    expect(await p.listProjects()).toEqual([
      {
        key: 'SCRUM',
        name: 'Sandbox',
        type: 'software',
        avatarUrl: null,
        openIssues: null,
        totalIssues: 22,
        url: 'https://x.atlassian.net/browse/SCRUM',
      },
    ])
    await p.listProjects(true)
    expect(searches).toEqual(['', '?refresh=true'])
    expect(p.features.projects).toBe(true)
  })
})

describe('F10-RF-01 F10-RF-05 F10-RF-06 histórico pela API', () => {
  it('lista com filtros e cursor, status por chave e texto para o agente', async () => {
    const searches: string[] = []
    let statusBody: unknown = null
    server.use(
      http.get(api('/api/v1/jira/issues'), ({ request }) => {
        searches.push(new URL(request.url).search)
        return HttpResponse.json({
          items: [
            {
              key: 'ABC-1',
              url: 'https://x.atlassian.net/browse/ABC-1',
              project_key: 'ABC',
              issue_type: 'Story',
              summary: 'Pix',
              readiness: 'agent_ready',
              operation: 'created',
              created_at: '2026-11-17T12:00:00Z',
              updated_at: null,
              conversation_id: null,
              conversation_title: null,
              has_spec: true,
            },
          ],
          next_cursor: 'c2',
        })
      }),
      http.post(api('/api/v1/jira/issues/status'), async ({ request }) => {
        statusBody = await request.json()
        return HttpResponse.json({
          statuses: { 'ABC-1': { name: 'A fazer', category: 'new' }, 'ABC-9': null },
        })
      }),
      http.get(api('/api/v1/jira/issues/ABC-1/agent-prompt'), () =>
        HttpResponse.json({ key: 'ABC-1', text: 'Implemente a issue ABC-1' }),
      ),
    )
    const p = product()

    const page = await p.listIssues(
      { projectKey: 'ABC', type: 'Story', readiness: 'agent_ready', from: '2026-11-10T00:00:00Z' },
      'c1',
    )

    expect(page.nextCursor).toBe('c2')
    expect(page.items[0]).toMatchObject({
      key: 'ABC-1',
      type: 'Story',
      title: 'Pix',
      conversationId: null,
      hasSpec: true,
    })
    const params = new URLSearchParams(searches[0])
    expect(Object.fromEntries(params)).toEqual({
      limit: '25',
      project: 'ABC',
      type: 'Story',
      readiness: 'agent_ready',
      from: '2026-11-10T00:00:00Z',
      cursor: 'c1',
    })
    expect(await p.issueStatuses(['ABC-1', 'ABC-9'])).toEqual({
      'ABC-1': { name: 'A fazer', category: 'new' },
      'ABC-9': null,
    })
    expect(statusBody).toEqual({ keys: ['ABC-1', 'ABC-9'] })
    expect(await p.agentPrompt('ABC-1')).toBe('Implemente a issue ABC-1')
  })
})

describe('F11-RF-01 uso pela API', () => {
  it('mapeia o consumo do dia e os 7 dias, o último é hoje', async () => {
    const days = [
      '2026-11-12',
      '2026-11-13',
      '2026-11-14',
      '2026-11-15',
      '2026-11-16',
      '2026-11-17',
      '2026-11-18',
    ]
    server.use(
      http.get(api('/api/v1/me/usage'), () =>
        HttpResponse.json({
          messages_today: 3,
          message_limit: 20,
          tokens_today: 1500,
          token_limit: 200000,
          resets_at: '2026-11-19T03:00:00Z',
          last_7_days: days.map((day, i) => ({ day, messages: i })),
        }),
      ),
    )
    const p = product()

    const usage = await p.getUsage()

    expect(p.features.usage).toBe(true)
    expect(usage).toEqual({
      usedToday: 3,
      dailyLimit: 20,
      last7Days: [
        { label: 'Thu', count: 0 },
        { label: 'Fri', count: 1 },
        { label: 'Sat', count: 2 },
        { label: 'Sun', count: 3 },
        { label: 'Mon', count: 4 },
        { label: 'Tue', count: 5 },
        { label: 'today', count: 6 },
      ],
    })
  })
})

describe('F19-RT-08 vínculo com o Confluence pela API', () => {
  const space = {
    key: 'SCRUM',
    name: 'Minha equipe',
    url: 'https://x.atlassian.net/wiki/spaces/SCRUM',
  }

  it('lê a sugestão, vincula com PUT, desvincula e busca espaços', async () => {
    const calls: string[] = []
    const path = '/api/v1/jira/projects/SCRUM/confluence'
    server.use(
      http.get(api(path), () =>
        HttpResponse.json({
          link: null,
          suggestion: { space, source: 'same-key' },
          available: true,
        }),
      ),
      http.put(api(path), async ({ request }) => {
        calls.push(`PUT ${JSON.stringify(await request.json())}`)
        return HttpResponse.json({ space, source: 'same-key', linked_at: '2026-11-20T12:00:00Z' })
      }),
      http.delete(api(path), () => {
        calls.push('DELETE')
        return new HttpResponse(null, { status: 204 })
      }),
      http.get(api('/api/v1/confluence/spaces'), ({ request }) => {
        calls.push(`GET ${new URL(request.url).search}`)
        return HttpResponse.json([space])
      }),
    )
    const p = product()

    expect(await p.getProjectDocs('SCRUM')).toEqual({
      link: null,
      suggestion: { space, source: 'same-key' },
      available: true,
      canCreate: false,
    })
    expect((await p.linkProjectDocs('SCRUM', 'SCRUM')).link).toEqual({
      space,
      source: 'same-key',
      linkedAt: '2026-11-20T12:00:00Z',
    })
    await p.unlinkProjectDocs('SCRUM')
    expect(await p.searchDocSpaces('min')).toEqual([space])
    expect(calls).toEqual(['PUT {"space_key":"SCRUM"}', 'DELETE', 'GET ?q=min'])
    expect(p.features.docs).toBe(true)
  })
})
