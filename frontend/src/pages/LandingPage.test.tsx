import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from '../App'
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
