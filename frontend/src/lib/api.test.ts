import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { api, server } from '../test/server'
import { ApiError, apiFetch } from './api'

describe('F03-RT-03 cliente da API', () => {
  it('envia o ID token no Authorization', async () => {
    let seen: string | null = null
    server.use(
      http.get(api('/api/v1/me'), ({ request }) => {
        seen = request.headers.get('Authorization')
        return HttpResponse.json({})
      }),
    )

    await apiFetch('/api/v1/me', async () => 'tok')

    expect(seen).toBe('Bearer tok')
  })

  it('em 401, renova o token e tenta uma vez', async () => {
    const getToken = vi.fn(async (force: boolean) => (force ? 'novo' : 'velho'))
    server.use(
      http.get(api('/api/v1/me'), ({ request }) =>
        request.headers.get('Authorization') === 'Bearer novo'
          ? HttpResponse.json({ ok: true })
          : new HttpResponse(null, { status: 401 }),
      ),
    )

    const response = await apiFetch('/api/v1/me', getToken)

    expect(await response.json()).toEqual({ ok: true })
    expect(getToken.mock.calls).toEqual([[false], [true]])
  })

  it('não tenta mais de uma vez e devolve o Problem Details', async () => {
    const getToken = vi.fn(async () => 'tok')
    server.use(
      http.get(api('/api/v1/me'), () =>
        HttpResponse.json(
          { code: 'unauthenticated', title: 'Não autenticado', detail: 'Entre de novo.' },
          { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )

    const error = await apiFetch('/api/v1/me', getToken).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 401, code: 'unauthenticated', message: 'Entre de novo.' })
    expect(getToken).toHaveBeenCalledTimes(2)
  })

  it('erro sem corpo JSON vira ApiError genérico', async () => {
    server.use(http.get(api('/api/v1/me'), () => new HttpResponse('falhou', { status: 500 })))

    await expect(apiFetch('/api/v1/me', async () => null)).rejects.toMatchObject({
      status: 500,
      code: 'http-500',
    })
  })
})

describe('F11-RT-07 App Check', () => {
  it('manda X-Firebase-AppCheck quando há token e segue sem ele se falhar', async () => {
    const seen: (string | null)[] = []
    server.use(
      http.get(api('/api/v1/me'), ({ request }) => {
        seen.push(request.headers.get('X-Firebase-AppCheck'))
        return HttpResponse.json({})
      }),
    )
    const { setAppCheckTokenGetter } = await import('./appCheck')

    setAppCheckTokenGetter(async () => 'app-check-1')
    await apiFetch('/api/v1/me', async () => 'tok')
    setAppCheckTokenGetter(async () => {
      throw new Error('reCAPTCHA fora do ar')
    })
    await apiFetch('/api/v1/me', async () => 'tok')
    setAppCheckTokenGetter(null)
    await apiFetch('/api/v1/me', async () => 'tok')

    expect(seen).toEqual(['app-check-1', null, null])
  })
})
