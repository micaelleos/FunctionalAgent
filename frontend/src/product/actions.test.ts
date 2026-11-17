import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { ApiError } from '../lib/api'
import { api, server } from '../test/server'
import { ActionProblem, type ApiAction, fromApiAction, toActionProblem } from './actions'
import { createHttpProductApi } from './http'

const update: ApiAction = {
  id: 'a2',
  kind: 'update_issue',
  status: 'pending',
  conversation_id: 'c1',
  preview: {
    issue_key: 'SCRUM-1',
    url: 'https://sandbox.atlassian.net/browse/SCRUM-1',
    issue_type: 'Story',
    summary: 'Login com e-mail',
    markdown: '## Objetivo\nNovo',
    sections: [{ title: 'Objetivo', markdown: 'Novo' }],
    priority: 'High',
    before: { summary: 'Login', markdown: 'Antigo', priority: 'Medium', labels: ['time-a'] },
  },
  readiness: {
    ready: false,
    rules: [
      { id: 'P-05', label: 'Fora de escopo', severity: 'obrigatória', passed: false, detail: '' },
    ],
  },
  labels: ['specflow', 'time-a'],
  created_at: '2026-11-16T12:00:00Z',
  expires_at: '2026-11-17T12:00:00Z',
}

describe('F06-RF-06 mapeamento da ação da API', () => {
  it('atualização vira antes/depois por campo', () => {
    const action = fromApiAction(update)

    expect(action.issueKey).toBe('SCRUM-1')
    expect(action.projectKey).toBeNull()
    expect(action.changes).toEqual([
      { field: 'summary', before: 'Login', after: 'Login com e-mail' },
      { field: 'description', before: 'Antigo', after: '## Objetivo\nNovo' },
      { field: 'priority', before: 'Medium', after: 'High' },
      { field: 'labels', before: 'time-a', after: 'specflow, time-a' },
    ])
    expect(action.readiness?.rules[0]).toMatchObject({ id: 'P-05', passed: false })
  })

  it('resultado e erro', () => {
    const done = fromApiAction({
      ...update,
      status: 'done',
      result: { issue_key: 'SCRUM-1', url: 'https://x/browse/SCRUM-1' },
    })
    const failed = fromApiAction({
      ...update,
      status: 'failed',
      error: { code: 'jira-forbidden', message: 'Sem permissão.' },
    })

    expect([done.resultKey, done.resultUrl]).toEqual(['SCRUM-1', 'https://x/browse/SCRUM-1'])
    expect(failed.error).toBe('Sem permissão.')
  })

  it('erro da API com a ação vira ActionProblem; sem ação, segue igual', () => {
    const withAction = new ApiError(409, 'action-not-pending', 'Já tratada', {
      action: { ...update, status: 'rejected' },
    })
    const plain = new ApiError(500, 'http-500', 'falhou')

    const problem = toActionProblem(withAction)
    expect(problem).toBeInstanceOf(ActionProblem)
    expect((problem as ActionProblem).action.status).toBe('rejected')
    expect(toActionProblem(plain)).toBe(plain)
  })
})

describe('F06-RF-02 confirmar e recusar pela API', () => {
  it('confirmar chama POST /actions/{id}/confirm com o token', async () => {
    const seen: { url: string; auth: string | null }[] = []
    server.use(
      http.post(api('/api/v1/actions/a2/confirm'), ({ request }) => {
        seen.push({ url: request.url, auth: request.headers.get('Authorization') })
        return HttpResponse.json({
          ...update,
          status: 'done',
          result: { issue_key: 'SCRUM-1', url: 'https://x/browse/SCRUM-1' },
        })
      }),
    )
    const product = createHttpProductApi(async () => 'token-1')

    const action = await product.confirmAction('a2')

    expect(action.status).toBe('done')
    expect(seen).toEqual([{ url: api('/api/v1/actions/a2/confirm'), auth: 'Bearer token-1' }])
  })

  it('erro com a ação no corpo chega ao cartão como ActionProblem', async () => {
    server.use(
      http.post(api('/api/v1/actions/a2/reject'), () =>
        HttpResponse.json(
          { code: 'action-expired', detail: 'Expirou.', action: { ...update, status: 'expired' } },
          { status: 410, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )
    const product = createHttpProductApi(async () => 'token-1')

    const error = await product.rejectAction('a2').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ActionProblem)
    expect((error as ActionProblem).action.status).toBe('expired')
    expect((error as ActionProblem).message).toBe('Expirou.')
  })
})
