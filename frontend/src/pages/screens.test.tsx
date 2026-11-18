import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { createDemoProductApi } from '../product/demo'
import type { ProductApi } from '../product/types'
import { unavailableProductApi } from '../product/unavailable'
import { ALICE, fakeAuth } from '../test/fakeAuth'

afterEach(() => vi.restoreAllMocks())

const NOW = Date.parse('2026-11-14T12:00:00Z')

function renderApp(path: string, productApi: ProductApi = createDemoProductApi(() => NOW)) {
  render(<App authClient={fakeAuth(ALICE).client} productApi={productApi} initialPath={path} />)
  return productApi
}

describe('F08-RF-10 navegação entre as telas principais', () => {
  it('o menu lateral leva a cada tela', async () => {
    renderApp('/chat')
    const user = userEvent.setup()
    const nav = await screen.findByRole('navigation', { name: 'Main' })

    for (const [link, heading] of [
      ['Jira projects', 'Jira projects'],
      ['Created issues', 'Created issues'],
      ['Settings', 'Settings'],
      ['My account', 'My account'],
      ['Chat', 'Chat'],
    ]) {
      await user.click(within(nav).getByRole('link', { name: link }))
      expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
    }
  })

  it('exige login', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/projects" />)

    expect(
      await screen.findByRole('heading', { name: 'Sign in to SpecFlow AI' }),
    ).toBeInTheDocument()
  })
})

describe('F08-RF-09 menu em celular', () => {
  it('o botão abre e fecha o menu e informa o estado', async () => {
    renderApp('/chat')
    const user = userEvent.setup()
    const toggle = await screen.findByRole('button', { name: 'Open menu' })

    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await user.click(toggle)
    expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })
})

describe('F08-RT-08 produção sem dados inventados', () => {
  it('cada tela mostra o estado vazio quando a feature ainda não existe', async () => {
    renderApp('/projects', unavailableProductApi)
    expect(await screen.findByRole('link', { name: 'Connect Jira' })).toBeInTheDocument()
    expect(screen.getByText('Jira not connected')).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('com o envio desligado, o chat avisa e não deixa enviar', async () => {
    renderApp('/chat', unavailableProductApi)
    const user = userEvent.setup()

    expect(await screen.findByText(/Sending messages is turned off/)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Message'), 'Olá')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('configurações mostra o formulário desabilitado com o aviso da F04', async () => {
    renderApp('/settings', unavailableProductApi)

    expect(await screen.findByText(/arrives in the next release \(F04\)/)).toBeInTheDocument()
    expect(screen.getByLabelText('API token')).toBeDisabled()
  })

  it('issues e uso ficam vazios', async () => {
    renderApp('/issues', unavailableProductApi)
    expect(await screen.findByText(/No issues yet/)).toBeInTheDocument()
  })

  it('o modo demonstração é anunciado', async () => {
    renderApp('/chat')
    expect(await screen.findByRole('note')).toHaveTextContent('Demo data')
  })
})

describe('F09 tela de projetos', () => {
  it('lista os projetos e filtra pela busca', async () => {
    renderApp('/projects')
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Payments' })).toBeInTheDocument()
    expect(screen.getByText('5 projects your Jira account can see.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Search by name or key'), 'auth')
    expect(screen.getByRole('heading', { name: 'Authentication' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payments' })).not.toBeInTheDocument()

    await user.clear(screen.getByLabelText('Search by name or key'))
    await user.type(screen.getByLabelText('Search by name or key'), 'xyz')
    expect(screen.getByText('No project matches “xyz”.')).toBeInTheDocument()
  })

  it('"Chat about this project" abre o chat com o projeto fixado', async () => {
    renderApp('/projects')
    const user = userEvent.setup()

    const [first] = await screen.findAllByRole('link', { name: 'Chat about this project' })
    await user.click(first)

    expect(await screen.findByText('Pinned project: PAG')).toBeInTheDocument()
  })

  it('links para o Jira abrem em outra aba com rel seguro', async () => {
    renderApp('/projects')
    const [link] = await screen.findAllByRole('link', { name: 'Open in Jira' })
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('target', '_blank')
  })
})

describe('F10 tela de issues criadas', () => {
  it('filtra por tipo e projeto e atualiza o status', async () => {
    renderApp('/issues')
    const user = userEvent.setup()
    const table = await screen.findByRole('table')

    expect(within(table).getAllByRole('row')).toHaveLength(5) // cabeçalho + 4
    await user.click(screen.getByRole('button', { name: 'Task' }))
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Task' })).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: 'All' }))
    await user.selectOptions(screen.getByLabelText('Project'), 'AUTH')
    expect(within(table).getAllByRole('row')).toHaveLength(3)

    await user.click(screen.getByRole('button', { name: 'Refresh Jira status' }))
    expect(await within(table).findAllByText(/To Do|In Progress|Done/)).not.toHaveLength(0)
  })

  it('a origem leva à conversa', async () => {
    renderApp('/issues')
    const user = userEvent.setup()

    const [origin] = await screen.findAllByRole('link', { name: 'Refine social login' })
    await user.click(origin)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Refine social login' }),
    ).toBeInTheDocument()
  })
})

describe('F04 tela de configurações do Jira', () => {
  it('mostra a conexão com o token mascarado, troca e remove', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderApp('/settings')
    const user = userEvent.setup()

    expect(await screen.findByText('••••••••1234')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Replace token' }))
    // Site e e-mail vêm preenchidos com a conexão atual; o token, nunca.
    expect(screen.getByLabelText('Site URL')).toHaveValue('https://jira.example.com')
    expect(screen.getByLabelText('API token')).toHaveValue('')
    await user.clear(screen.getByLabelText('Site URL'))
    await user.type(screen.getByLabelText('Site URL'), 'https://acme.atlassian.net')
    await user.clear(screen.getByLabelText('Atlassian account email'))
    await user.type(screen.getByLabelText('Atlassian account email'), 'po@acme.dev')
    await user.type(screen.getByLabelText('API token'), 'curto')
    await user.click(screen.getByRole('button', { name: 'Validate and save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Jira rejected the credential')

    await user.clear(screen.getByLabelText('API token'))
    await user.type(screen.getByLabelText('API token'), 'token-novo-9876')
    await user.click(screen.getByRole('button', { name: 'Validate and save' }))
    expect(await screen.findByText('••••••••9876')).toBeInTheDocument()
    expect(screen.getAllByText('acme.atlassian.net').length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: 'Remove connection' }))
    expect(await screen.findByRole('heading', { name: 'Connect Jira' })).toBeInTheDocument()
    expect(screen.getByText('Jira not connected')).toBeInTheDocument()
  })

  it('explica como criar o token', async () => {
    renderApp('/settings')
    expect(await screen.findByRole('link', { name: 'Open the API tokens page' })).toHaveAttribute(
      'href',
      'https://id.atlassian.com/manage-profile/security/api-tokens',
    )
  })
})

describe('F08-RF-04 cartão de ação no chat', () => {
  it('confirmar cria a issue e mostra a chave e o link', async () => {
    renderApp('/chat/c1')
    const user = userEvent.setup()

    const card = await screen.findByRole('region', { name: 'Create Story in PAG' })
    expect(within(card).getByText('Pay for the order with Pix')).toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: 'Confirm and create' }))

    expect(await within(card).findByRole('status')).toHaveTextContent('Created as PAG-142')
    expect(within(card).getByRole('link', { name: 'Open in Jira' })).toBeInTheDocument()
  })

  it('rejeitar não envia nada', async () => {
    renderApp('/chat/c1')
    const user = userEvent.setup()

    const card = await screen.findByRole('region', { name: 'Create Story in PAG' })
    await user.click(within(card).getByRole('button', { name: 'Reject' }))

    expect(await within(card).findByRole('status')).toHaveTextContent('Nothing was sent to Jira')
  })
})

describe('F08-RF-08 conversa vazia e envio', () => {
  it('a sugestão preenche o campo; Enter envia e abre a conversa nova', async () => {
    renderApp('/chat')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Pix checkout/ }))
    expect(screen.getByLabelText('Message')).toHaveValue('Write an epic for Pix checkout')

    await user.type(screen.getByLabelText('Message'), '{Enter}')
    expect(await screen.findByText(/streams its answer here/)).toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toHaveValue('')
    expect(
      await screen.findByRole('heading', { level: 1, name: /^Write an epic/ }),
    ).toBeInTheDocument()
  })

  it('F08-RF-07 falha no envio mantém o texto', async () => {
    const api = createDemoProductApi(() => NOW)
    api.streamMessage = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    renderApp('/chat', api)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Message'), 'Olá{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't reach the server")
    expect(screen.getByLabelText('Message')).toHaveValue('Olá')
  })

  it('Shift+Enter quebra a linha sem enviar', async () => {
    const api = createDemoProductApi(() => NOW)
    const send = vi.spyOn(api, 'streamMessage')
    renderApp('/chat', api)
    const user = userEvent.setup()

    await user.type(
      await screen.findByLabelText('Message'),
      'linha 1{Shift>}{Enter}{/Shift}linha 2',
    )

    expect(screen.getByLabelText('Message')).toHaveValue('linha 1\nlinha 2')
    expect(send).not.toHaveBeenCalled()
  })

  it('o bloco de código tem botão copiar', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    renderApp('/chat/c1')

    await user.click(await screen.findByRole('button', { name: 'Copy code' }))

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining('Scenario')))
    expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument()
  })
})

describe('F11 uso na conta', () => {
  it('mostra o uso de hoje e dos últimos 7 dias', async () => {
    renderApp('/account')

    expect(await screen.findByText('18 of 20 messages')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /last 7 days/ })).toBeInTheDocument()
  })
})
