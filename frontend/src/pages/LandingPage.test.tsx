import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from '../App'
import { SUPPORT_URL } from '../lib/links'
import { ALICE, fakeAuth } from '../test/fakeAuth'

describe('F08-RF-11 public landing page', () => {
  it('presents the product and links to sign-up and sign-in', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/" />)

    expect(
      await screen.findByRole('heading', { level: 1, name: /coding agent can actually ship/ }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Get started free/ })).toHaveAttribute(
      'href',
      '/signup',
    )
    expect(screen.getByRole('link', { name: 'I have an account' })).toHaveAttribute(
      'href',
      '/login',
    )
    expect(
      screen.getByRole('heading', { name: 'Every issue follows the same contract' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Acceptance criteria' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'How it works' })).toBeInTheDocument()
    expect(screen.getByText('Illustrative conversation')).toBeInTheDocument()
  })

  it('signed-in users go straight to the chat', async () => {
    render(<App authClient={fakeAuth(ALICE).client} initialPath="/" />)

    expect(await screen.findByRole('heading', { level: 1, name: 'Chat' })).toBeInTheDocument()
  })
})

describe('F12-RF-03 F12-RF-04 rodapé: ajuda, privacidade e status da API', () => {
  it('tem "Help" (issues do GitHub), "Privacy" e o status da API', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/" />)

    const footer = await screen.findByRole('contentinfo')
    expect(within(footer).getByRole('link', { name: /Help/ })).toHaveAttribute('href', SUPPORT_URL)
    expect(within(footer).getByRole('link', { name: 'Privacy' })).toHaveAttribute(
      'href',
      '/privacy',
    )
    expect(await within(footer).findByText('API: ok')).toBeInTheDocument()
  })

  it.each(['/about', '/sobre'])('%s (página antiga) leva à página inicial', async (path) => {
    render(<App authClient={fakeAuth().client} initialPath={path} />)

    expect(
      await screen.findByRole('heading', { level: 1, name: /coding agent can actually ship/ }),
    ).toBeInTheDocument()
  })
})
