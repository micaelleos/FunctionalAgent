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
    const nav = await screen.findByRole('navigation', { name: 'Principal' })

    for (const [link, heading] of [
      ['Projetos Jira', 'Projetos Jira'],
      ['Issues criadas', 'Issues criadas'],
      ['Configurações', 'Configurações'],
      ['Minha conta', 'Minha conta'],
      ['Chat', 'Chat'],
    ]) {
      await user.click(within(nav).getByRole('link', { name: link }))
      expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
    }
  })

  it('exige login', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/projetos" />)

    expect(
      await screen.findByRole('heading', { name: 'Entrar no SpecFlow AI' }),
    ).toBeInTheDocument()
  })
})

describe('F08-RF-09 menu em celular', () => {
  it('o botão abre e fecha o menu e informa o estado', async () => {
    renderApp('/chat')
    const user = userEvent.setup()
    const toggle = await screen.findByRole('button', { name: 'Abrir menu' })

    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await user.click(toggle)
    expect(screen.getByRole('button', { name: 'Fechar menu' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })
})

describe('F08-RT-08 produção sem dados inventados', () => {
  it('cada tela mostra o estado vazio quando a feature ainda não existe', async () => {
    renderApp('/projetos', unavailableProductApi)
    expect(await screen.findByRole('link', { name: 'Conectar o Jira' })).toBeInTheDocument()
    expect(screen.getByText('Jira não conectado')).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('o chat avisa que o agente chega em breve e não deixa enviar', async () => {
    renderApp('/chat', unavailableProductApi)
    const user = userEvent.setup()

    expect(await screen.findByText(/O agente chega em breve/)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Mensagem'), 'Olá')
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
  })

  it('configurações mostra o formulário desabilitado com o aviso da F04', async () => {
    renderApp('/configuracoes', unavailableProductApi)

    expect(await screen.findByText(/chega na próxima versão \(F04\)/)).toBeInTheDocument()
    expect(screen.getByLabelText('Token de API')).toBeDisabled()
  })

  it('issues e uso ficam vazios', async () => {
    renderApp('/issues', unavailableProductApi)
    expect(await screen.findByText(/Nenhuma issue criada ainda/)).toBeInTheDocument()
  })

  it('o modo demonstração é anunciado', async () => {
    renderApp('/chat')
    expect(await screen.findByRole('note')).toHaveTextContent('Dados de demonstração')
  })
})

describe('F09 tela de projetos', () => {
  it('lista os projetos e filtra pela busca', async () => {
    renderApp('/projetos')
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Pagamentos' })).toBeInTheDocument()
    expect(screen.getByText('5 projetos que a sua conta do Jira pode ver.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Buscar por nome ou chave'), 'auth')
    expect(screen.getByRole('heading', { name: 'Autenticação' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Pagamentos' })).not.toBeInTheDocument()

    await user.clear(screen.getByLabelText('Buscar por nome ou chave'))
    await user.type(screen.getByLabelText('Buscar por nome ou chave'), 'xyz')
    expect(screen.getByText('Nenhum projeto com “xyz”.')).toBeInTheDocument()
  })

  it('"Conversar sobre este projeto" abre o chat com o projeto fixado', async () => {
    renderApp('/projetos')
    const user = userEvent.setup()

    const [first] = await screen.findAllByRole('link', { name: 'Conversar sobre este projeto' })
    await user.click(first)

    expect(await screen.findByText('Projeto fixado: PAG')).toBeInTheDocument()
  })

  it('links para o Jira abrem em outra aba com rel seguro', async () => {
    renderApp('/projetos')
    const [link] = await screen.findAllByRole('link', { name: 'Abrir no Jira' })
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
    await user.click(screen.getByRole('button', { name: 'Tarefa' }))
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Tarefa' })).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: 'Todos' }))
    await user.selectOptions(screen.getByLabelText('Projeto'), 'AUTH')
    expect(within(table).getAllByRole('row')).toHaveLength(3)

    await user.click(screen.getByRole('button', { name: 'Atualizar status do Jira' }))
    expect(await within(table).findAllByText(/A fazer|Em andamento|Concluído/)).not.toHaveLength(0)
  })

  it('a origem leva à conversa', async () => {
    renderApp('/issues')
    const user = userEvent.setup()

    const [origin] = await screen.findAllByRole('link', { name: 'Refinar login social' })
    await user.click(origin)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Refinar login social' }),
    ).toBeInTheDocument()
  })
})

describe('F04 tela de configurações do Jira', () => {
  it('mostra a conexão com o token mascarado, troca e remove', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderApp('/configuracoes')
    const user = userEvent.setup()

    expect(await screen.findByText('••••••••1234')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Trocar token' }))
    await user.type(screen.getByLabelText('URL do site'), 'https://acme.atlassian.net')
    await user.type(screen.getByLabelText('E-mail da conta Atlassian'), 'po@acme.dev')
    await user.type(screen.getByLabelText('Token de API'), 'curto')
    await user.click(screen.getByRole('button', { name: 'Validar e salvar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('O Jira recusou o e-mail ou o token')

    await user.clear(screen.getByLabelText('Token de API'))
    await user.type(screen.getByLabelText('Token de API'), 'token-novo-9876')
    await user.click(screen.getByRole('button', { name: 'Validar e salvar' }))
    expect(await screen.findByText('••••••••9876')).toBeInTheDocument()
    expect(screen.getAllByText('acme.atlassian.net').length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: 'Remover conexão' }))
    expect(await screen.findByRole('heading', { name: 'Conectar o Jira' })).toBeInTheDocument()
    expect(screen.getByText('Jira não conectado')).toBeInTheDocument()
  })

  it('explica como criar o token', async () => {
    renderApp('/configuracoes')
    expect(await screen.findByRole('link', { name: 'Abrir a página de tokens' })).toHaveAttribute(
      'href',
      'https://id.atlassian.com/manage-profile/security/api-tokens',
    )
  })
})

describe('F08-RF-04 cartão de ação no chat', () => {
  it('confirmar cria a issue e mostra a chave e o link', async () => {
    renderApp('/chat/c1')
    const user = userEvent.setup()

    const card = await screen.findByRole('region', { name: 'Ação proposta · Criar no Jira' })
    expect(within(card).getByText('Pagar o pedido com Pix')).toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: 'Confirmar e criar' }))

    expect(await within(card).findByRole('status')).toHaveTextContent('Criada como PAG-142')
    expect(within(card).getByRole('link', { name: 'Abrir no Jira' })).toBeInTheDocument()
  })

  it('rejeitar não envia nada', async () => {
    renderApp('/chat/c1')
    const user = userEvent.setup()

    const card = await screen.findByRole('region', { name: 'Ação proposta · Criar no Jira' })
    await user.click(within(card).getByRole('button', { name: 'Rejeitar' }))

    expect(await within(card).findByRole('status')).toHaveTextContent('Nada foi enviado ao Jira')
  })
})

describe('F08-RF-08 conversa vazia e envio', () => {
  it('a sugestão preenche o campo; Enter envia e abre a conversa nova', async () => {
    renderApp('/chat')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /checkout com Pix/ }))
    expect(screen.getByLabelText('Mensagem')).toHaveValue(
      'Escrever um épico para o checkout com Pix',
    )

    await user.type(screen.getByLabelText('Mensagem'), '{Enter}')
    expect(await screen.findByText(/Isto é uma demonstração/)).toBeInTheDocument()
    expect(screen.getByLabelText('Mensagem')).toHaveValue('')
    expect(
      await screen.findByRole('heading', { level: 1, name: /^Escrever um épico/ }),
    ).toBeInTheDocument()
  })

  it('F08-RF-07 falha no envio mantém o texto', async () => {
    const api = createDemoProductApi(() => NOW)
    api.sendMessage = vi.fn().mockRejectedValue(new Error('rede'))
    renderApp('/chat', api)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Mensagem'), 'Olá{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('Algo deu errado.')
    expect(screen.getByLabelText('Mensagem')).toHaveValue('Olá')
  })

  it('Shift+Enter quebra a linha sem enviar', async () => {
    const api = createDemoProductApi(() => NOW)
    const send = vi.spyOn(api, 'sendMessage')
    renderApp('/chat', api)
    const user = userEvent.setup()

    await user.type(
      await screen.findByLabelText('Mensagem'),
      'linha 1{Shift>}{Enter}{/Shift}linha 2',
    )

    expect(screen.getByLabelText('Mensagem')).toHaveValue('linha 1\nlinha 2')
    expect(send).not.toHaveBeenCalled()
  })

  it('o bloco de código tem botão copiar', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    renderApp('/chat/c1')

    await user.click(await screen.findByRole('button', { name: 'Copiar' }))

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining('Cenário')))
    expect(screen.getByRole('button', { name: 'Copiado' })).toBeInTheDocument()
  })
})

describe('F11 uso na conta', () => {
  it('mostra o uso de hoje e dos últimos 7 dias', async () => {
    renderApp('/conta')

    expect(await screen.findByText('18 de 50 mensagens')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /últimos 7 dias/ })).toBeInTheDocument()
  })
})
