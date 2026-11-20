import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import App from '../App'
import { createDemoProductApi } from '../product/demo'
import type { JiraProject, ProductApi } from '../product/types'
import { unavailableProductApi } from '../product/unavailable'
import { ALICE, fakeAuth } from '../test/fakeAuth'

const NOW = Date.parse('2026-11-20T12:00:00Z')
const project = (key: string): JiraProject => ({
  key,
  name: `Projeto ${key}`,
  type: 'software',
  avatarUrl: null,
  openIssues: 1,
  totalIssues: 2,
  url: `https://demo.atlassian.net/browse/${key}`,
})

function renderProjects(api: ProductApi) {
  render(<App authClient={fakeAuth(ALICE).client} productApi={api} initialPath="/projects" />)
}

const card = (name: string) => screen.getByRole('heading', { name }).closest('li') as HTMLElement

async function openDocs(name: string) {
  const c = await waitFor(() => card(name))
  await userEvent.click(within(c).getByRole('button', { name: 'Project docs' }))
  return c
}

describe('F19-RF-01 F19-RF-02 vínculo do projeto com o Confluence', () => {
  it('sugere o espaço com a mesma chave e só salva depois do Link', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('PAG')]
    const linkSpy = vi.spyOn(api, 'linkProjectDocs')
    renderProjects(api)

    const c = await openDocs('Projeto PAG')
    expect(await within(c).findByText('Found a space with the same key:')).toBeInTheDocument()
    expect(linkSpy).not.toHaveBeenCalled()

    await userEvent.click(within(c).getByRole('button', { name: 'Link' }))
    expect(linkSpy).toHaveBeenCalledWith('PAG', 'PAG')
    expect(
      await within(c).findByText('The agent reads this space before proposing issues:'),
    ).toBeInTheDocument()
    expect(
      within(c).getByRole('link', { name: 'Pagamentos — Documentação (PAG)' }),
    ).toHaveAttribute('href', 'https://demo.atlassian.net/wiki/spaces/PAG')

    await userEvent.click(within(c).getByRole('button', { name: 'Unlink' }))
    expect(await within(c).findByText('Found a space with the same key:')).toBeInTheDocument()
  })

  it('sem sugestão, escolhe um espaço pela busca', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('BI')]
    renderProjects(api)

    const c = await openDocs('Projeto BI')
    await userEvent.click(await within(c).findByRole('button', { name: 'Choose another space' }))
    await userEvent.type(within(c).getByLabelText('Search spaces'), 'auth')
    await userEvent.click(await within(c).findByRole('button', { name: 'Link Autenticação' }))
    expect(await within(c).findByRole('link', { name: 'Autenticação (AUTH)' })).toBeInTheDocument()
  })

  it('F19-RF-09 conta sem Confluence vê o aviso e o resto da tela segue', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('PAG')]
    api.getProjectDocs = async () => ({ link: null, suggestion: null, available: false })
    renderProjects(api)

    const c = await openDocs('Projeto PAG')
    expect(
      await within(c).findByText(
        'Your Atlassian account has no access to Confluence on this site.',
      ),
    ).toBeInTheDocument()
    expect(within(c).getByRole('link', { name: 'Chat about this project' })).toBeInTheDocument()
  })

  it('sem a feature, o painel não aparece', () => {
    expect(unavailableProductApi.features.docs).toBe(false)
  })
})

describe('F20-RF-01 criar o espaço a partir de Projects', () => {
  it('sem espaço e com a escrita ligada, "Create space" abre o chat do projeto com o pedido', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('NOVO')]
    api.getProjectDocs = async () => ({
      link: null,
      suggestion: null,
      available: true,
      canCreate: true,
    })
    renderProjects(api)

    const c = await openDocs('Projeto NOVO')
    await userEvent.click(await within(c).findByRole('link', { name: 'Create space' }))

    expect(await screen.findByLabelText('Message')).toHaveValue(
      'Create the documentation space for this project in Confluence, from the SpecFlow template.',
    )
  })

  it('sem a escrita ligada, só a escolha de um espaço existente', async () => {
    const api = createDemoProductApi(() => NOW)
    api.listProjects = async () => [project('NOVO')]
    api.getProjectDocs = async () => ({ link: null, suggestion: null, available: true })
    renderProjects(api)

    const c = await openDocs('Projeto NOVO')
    expect(await within(c).findByText('No space found. Pick one to link.')).toBeInTheDocument()
    expect(within(c).queryByRole('link', { name: 'Create space' })).not.toBeInTheDocument()
  })
})
