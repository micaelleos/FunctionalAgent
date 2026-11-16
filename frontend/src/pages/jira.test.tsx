import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { ALICE, fakeAuth } from '../test/fakeAuth'
import { api, server } from '../test/server'

// Tela de configurações do Jira contra a API real (createHttpProductApi), com o backend simulado
// pelo MSW no formato de /api/v1/jira/connections (F04).
const TOKEN = 'ATATT-token-de-teste-9876'
const BASE = '/api/v1/jira/connections'

type Connection = {
  id: string
  site_url: string
  email: string
  account_name: string
  token_hint: string
  status: 'ok' | 'invalid'
  last_validated_at: string
}

let stored: Connection | null
const requests: { method: string; path: string; body: unknown }[] = []

const problem = (status: number, code: string, detail: string) =>
  HttpResponse.json({ status, code, title: code, detail }, { status })

function backend() {
  const save = async ({ request }: { request: Request }) => {
    const body = (await request.json()) as { site_url: string; email: string; api_token: string }
    requests.push({ method: request.method, path: new URL(request.url).pathname, body })
    if (!body.site_url.startsWith('https://') || !body.site_url.includes('.atlassian.net')) {
      return problem(422, 'jira-invalid-url', 'Informe uma URL https://<seu-site>.atlassian.net')
    }
    if (body.api_token !== TOKEN && body.api_token !== 'ATATT-novo-5555') {
      return problem(422, 'jira-invalid-credentials', 'recusado')
    }
    stored = {
      id: 'conn-1',
      site_url: body.site_url.replace(/\/$/, ''),
      email: body.email,
      account_name: 'PO Teste',
      token_hint: body.api_token.slice(-4),
      status: 'ok',
      last_validated_at: '2026-11-16T12:00:00Z',
    }
    return HttpResponse.json(stored, { status: request.method === 'POST' ? 201 : 200 })
  }
  server.use(
    http.get(api(BASE), () => HttpResponse.json(stored ? [stored] : [])),
    http.post(api(BASE), save),
    http.put(api(`${BASE}/:id`), save),
    http.delete(api(`${BASE}/:id`), ({ request }) => {
      requests.push({ method: 'DELETE', path: new URL(request.url).pathname, body: null })
      stored = null
      return new HttpResponse(null, { status: 204 })
    }),
    http.post(api(`${BASE}/:id/validate`), () => {
      stored = { ...stored!, status: 'invalid' } // o token foi revogado no Jira
      return HttpResponse.json(stored)
    }),
  )
}

beforeEach(() => {
  stored = null
  requests.length = 0
  backend()
})
afterEach(() => vi.restoreAllMocks())

const renderAt = (path: string) =>
  render(<App authClient={fakeAuth(ALICE).client} initialPath={path} />)

async function fillAndSave(site: string, token: string) {
  const user = userEvent.setup()
  await user.clear(await screen.findByLabelText('URL do site'))
  await user.type(screen.getByLabelText('URL do site'), site)
  await user.clear(screen.getByLabelText('E-mail da conta Atlassian'))
  await user.type(screen.getByLabelText('E-mail da conta Atlassian'), 'po@teste.dev')
  await user.type(screen.getByLabelText('Token de API'), token)
  await user.click(screen.getByRole('button', { name: 'Validar e salvar' }))
  return user
}

describe('F04-RF-01 F04-RF-02 F04-RF-04 conectar o Jira (AT-F04-01)', () => {
  it('valida, mostra a conta e o token só mascarado', async () => {
    renderAt('/configuracoes')
    await fillAndSave('https://sandbox.atlassian.net', TOKEN)

    expect(await screen.findByText('Conectado como PO Teste')).toBeInTheDocument()
    expect(screen.getByText('••••••••9876')).toBeInTheDocument()
    expect(screen.queryByDisplayValue(TOKEN)).not.toBeInTheDocument()
    expect(document.body.textContent).not.toContain(TOKEN)
    expect(requests).toEqual([
      {
        method: 'POST',
        path: BASE,
        body: {
          site_url: 'https://sandbox.atlassian.net',
          email: 'po@teste.dev',
          api_token: TOKEN,
        },
      },
    ])
    expect(screen.getByText('Jira conectado · sandbox.atlassian.net')).toBeInTheDocument()
  })
})

describe('F04-RF-03 erros ao conectar (AT-F04-02, AT-F04-03)', () => {
  it('credencial recusada não é salva', async () => {
    renderAt('/configuracoes')
    await fillAndSave('https://sandbox.atlassian.net', 'token-errado-123')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'O Jira recusou a credencial. Verifique e-mail e token.',
    )
    expect(stored).toBeNull()
  })

  it('URL fora do padrão', async () => {
    renderAt('/configuracoes')
    await fillAndSave('https://169.254.169.254', TOKEN)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Informe uma URL https://<seu-site>.atlassian.net',
    )
  })
})

describe('F04-RF-05 trocar e remover (AT-F04-05)', () => {
  it('troca com PUT e remove; Projetos volta a pedir a conexão', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    stored = {
      id: 'conn-1',
      site_url: 'https://sandbox.atlassian.net',
      email: 'po@teste.dev',
      account_name: 'PO Teste',
      token_hint: '9876',
      status: 'ok',
      last_validated_at: '2026-11-16T12:00:00Z',
    }
    renderAt('/configuracoes')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Trocar token' }))
    expect(screen.getByLabelText('URL do site')).toHaveValue('https://sandbox.atlassian.net')
    await user.type(screen.getByLabelText('Token de API'), 'ATATT-novo-5555')
    await user.click(screen.getByRole('button', { name: 'Validar e salvar' }))
    expect(await screen.findByText('••••••••5555')).toBeInTheDocument()
    expect(requests[requests.length - 1]).toMatchObject({ method: 'PUT', path: `${BASE}/conn-1` })

    await user.click(screen.getByRole('button', { name: 'Remover conexão' }))
    expect(await screen.findByRole('heading', { name: 'Conectar o Jira' })).toBeInTheDocument()
    expect(requests[requests.length - 1]).toMatchObject({
      method: 'DELETE',
      path: `${BASE}/conn-1`,
    })

    const nav = screen.getByRole('navigation', { name: 'Principal' })
    await user.click(within(nav).getByRole('link', { name: 'Projetos Jira' }))
    expect(await screen.findByText('Conecte sua conta do Jira')).toBeInTheDocument()
  })
})

describe('F04-RF-06 token revogado pede reconexão (AT-F04-04)', () => {
  it('"Testar conexão" marca expirada e o aviso aparece nas outras telas', async () => {
    stored = {
      id: 'conn-1',
      site_url: 'https://sandbox.atlassian.net',
      email: 'po@teste.dev',
      account_name: 'PO Teste',
      token_hint: '9876',
      status: 'ok',
      last_validated_at: '2026-11-16T12:00:00Z',
    }
    renderAt('/configuracoes')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Testar conexão' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Sua conexão com o Jira expirou')
    expect(screen.getByText('Expirada')).toBeInTheDocument()

    const nav = screen.getByRole('navigation', { name: 'Principal' })
    await user.click(within(nav).getByRole('link', { name: 'Projetos Jira' }))
    const banner = await screen.findByRole('alert')
    expect(banner).toHaveTextContent('Sua conexão com o Jira expirou')
    await user.click(within(banner).getByRole('link', { name: 'Reconectar' }))
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Configurações' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reconectar' }))
    expect(screen.getByLabelText('URL do site')).toHaveValue('https://sandbox.atlassian.net')
  })
})

describe('F04-RF-07 como criar o token', () => {
  it('o painel explica e leva à página da Atlassian', async () => {
    renderAt('/configuracoes')
    expect(
      await screen.findByRole('heading', { name: 'Como criar o token de API' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir a página de tokens' })).toHaveAttribute(
      'href',
      'https://id.atlassian.com/manage-profile/security/api-tokens',
    )
    expect(screen.queryByText(/chega na próxima versão \(F04\)/)).not.toBeInTheDocument()
  })
})

describe('F08-RT-08 projetos enquanto a F09 não chega', () => {
  it('com o Jira conectado, diz que a lista vem na próxima versão em vez de "0 projetos"', async () => {
    stored = {
      id: 'conn-1',
      site_url: 'https://sandbox.atlassian.net',
      email: 'po@teste.dev',
      account_name: 'PO Teste',
      token_hint: '9876',
      status: 'ok',
      last_validated_at: '2026-11-16T12:00:00Z',
    }
    renderAt('/projetos')

    expect(
      await screen.findByRole('heading', { name: 'A lista de projetos chega na próxima versão' }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/0 projetos/)).not.toBeInTheDocument()
  })
})
