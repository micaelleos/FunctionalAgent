import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from '../App'
import { SUPPORT_URL } from '../lib/links'
import { fakeAuth } from '../test/fakeAuth'

const renderAt = (path: string) => render(<App authClient={fakeAuth().client} initialPath={path} />)

describe('F12-RF-03 AT-F12-03 About explica o fluxo e onde pedir ajuda', () => {
  it('sem login: os 4 passos, o suporte no GitHub e o status da API', async () => {
    renderAt('/about')

    const how = await screen.findByRole('region', { name: 'How it works' })
    const steps = within(how)
      .getAllByRole('listitem')
      .map((li) => within(li).getByRole('heading').textContent)
    expect(steps).toEqual([
      'Create an account',
      'Connect Jira',
      'Chat',
      'Confirm before anything is written',
    ])
    expect(screen.getByRole('link', { name: 'Open an issue on GitHub' })).toHaveAttribute(
      'href',
      SUPPORT_URL,
    )
    expect(await screen.findByText('API: ok')).toBeInTheDocument()
  })

  it('F12-RF-04 o link "Privacy" abre a página de privacidade sem login', async () => {
    renderAt('/about')

    await userEvent.setup().click(await screen.findByRole('link', { name: 'Privacy' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Privacy' })).toBeInTheDocument()
  })
})
