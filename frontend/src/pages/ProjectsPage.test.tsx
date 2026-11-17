import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { createDemoProductApi } from '../product/demo'
import type { JiraProject, ProductApi } from '../product/types'
import { ALICE, fakeAuth } from '../test/fakeAuth'

afterEach(() => vi.restoreAllMocks())

const NOW = Date.parse('2026-11-17T12:00:00Z')
const SITE = 'https://sandbox.atlassian.net'

const project = (key: string, extra: Partial<JiraProject> = {}): JiraProject => ({
  key,
  name: `Projeto ${key}`,
  type: 'software',
  avatarUrl: `${SITE}/rest/api/3/universal_avatar/view/type/project/avatar/1`,
  openIssues: 3,
  totalIssues: 22,
  url: `${SITE}/browse/${key}`,
  ...extra,
})

function renderApp(path: string, api: ProductApi) {
  render(<App authClient={fakeAuth(ALICE).client} productApi={api} initialPath={path} />)
}

const card = (name: string) => screen.getByRole('heading', { name }).closest('li') as HTMLElement

describe('F09-RF-01 F09-RF-02 cards dos projetos', () => {
  it('mostra avatar, nome, chave, tipo, abertas e total', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('SCRUM', { type: 'business' })]
    renderApp('/projects', api)

    const scrum = await waitFor(() => card('Projeto SCRUM'))
    expect(within(scrum).getByText('SCRUM · Business')).toBeInTheDocument()
    expect(scrum.querySelector('img')).toHaveAttribute('src', project('SCRUM').avatarUrl)
    expect(within(scrum).getByText('3').parentElement).toHaveTextContent('3 open')
    expect(within(scrum).getByText('22').parentElement).toHaveTextContent('22 total')
    expect(screen.getByText('1 project your Jira account can see.')).toBeInTheDocument()
  })

  it('F09-RT-04 contagem que falhou aparece como "—"', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('ABC', { openIssues: null, totalIssues: null })]
    renderApp('/projects', api)

    const abc = await waitFor(() => card('Projeto ABC'))
    expect(within(abc).getAllByText('—')).toHaveLength(2)
    expect(within(abc).getAllByText('not available')).toHaveLength(2)
  })

  it('avatar que não carrega vira as iniciais', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('PAG')]
    renderApp('/projects', api)

    const pag = await waitFor(() => card('Projeto PAG'))
    fireEvent.error(pag.querySelector('img') as HTMLImageElement)

    expect(within(pag).getByTestId('avatar-iniciais')).toHaveTextContent('PA')
    expect(pag.querySelector('img')).toBeNull()
  })
})

describe('F09-RF-03 filtro', () => {
  it('filtra por parte do nome ou da chave e avisa sem resultado', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [
      project('SCRUM', { name: 'Sandbox' }),
      project('DEMO', { name: 'Demonstração' }),
    ]
    renderApp('/projects', api)
    const user = userEvent.setup()
    const search = await screen.findByLabelText('Search by name or key')

    await user.type(search, 'dem')
    expect(screen.getByRole('heading', { name: 'Demonstração' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Sandbox' })).not.toBeInTheDocument()

    await user.clear(search)
    await user.type(search, 'scr')
    expect(screen.getByRole('heading', { name: 'Sandbox' })).toBeInTheDocument()

    await user.clear(search)
    await user.type(search, 'xyz')
    expect(screen.getByText('No project matches “xyz”.')).toBeInTheDocument()
  })
})

describe('F09-RF-04 F09-RF-05 ações do card', () => {
  it('"Open in Jira" abre /browse/KEY em outra aba; "Chat about this project" fixa o projeto', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('SCRUM')]
    renderApp('/projects', api)
    const user = userEvent.setup()
    const scrum = await waitFor(() => card('Projeto SCRUM'))

    const jira = within(scrum).getByRole('link', { name: 'Open in Jira' })
    expect(jira).toHaveAttribute('href', `${SITE}/browse/SCRUM`)
    expect(jira).toHaveAttribute('target', '_blank')
    expect(jira).toHaveAttribute('rel', 'noopener noreferrer')

    await user.click(within(scrum).getByRole('link', { name: 'Chat about this project' }))
    expect(await screen.findByText('Pinned project: SCRUM')).toBeInTheDocument()
  })
})

describe('F09-RF-07 atualizar', () => {
  it('"Refresh" pede a lista ignorando o cache', async () => {
    const api = createDemoProductApi(() => NOW)
    const list = vi
      .fn<ProductApi['listProjects']>()
      .mockResolvedValueOnce([project('OLD')])
      .mockResolvedValueOnce([project('NEW')])
    api.listProjects = list
    renderApp('/projects', api)
    const user = userEvent.setup()
    await screen.findByRole('heading', { name: 'Projeto OLD' })

    await user.click(screen.getByRole('button', { name: 'Refresh' }))

    expect(await screen.findByRole('heading', { name: 'Projeto NEW' })).toBeInTheDocument()
    expect(list.mock.calls).toEqual([[], [true]])
  })
})

describe('F09-RF-06 sem conexão', () => {
  it('orienta a conectar e não busca projetos', async () => {
    const api = createDemoProductApi(() => NOW)
    await api.disconnectJira()
    const list = vi.spyOn(api, 'listProjects')
    renderApp('/projects', api)

    expect(await screen.findByText('Connect your Jira account')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Connect Jira' })).toHaveAttribute('href', '/settings')
    expect(list).not.toHaveBeenCalled()
  })

  it('erro do Jira fora do ar aparece traduzido', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = () =>
      Promise.reject(Object.assign(new Error('x'), { code: 'jira-unreachable' }))
    renderApp('/projects', api)

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't reach that Jira site")
  })
})
