import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from '../App'
import { ALICE, fakeAuth } from '../test/fakeAuth'

describe('F08-RF-11 página inicial pública', () => {
  it('apresenta o produto e leva ao cadastro e ao login', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/" />)

    expect(
      await screen.findByRole('heading', { level: 1, name: /backlog no Jira/ }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Começar agora' })).toHaveAttribute('href', '/cadastro')
    expect(screen.getByRole('link', { name: 'Já tenho conta' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('heading', { name: 'Como funciona' })).toBeInTheDocument()
    expect(screen.getByText('Exemplo ilustrativo de conversa')).toBeInTheDocument()
  })

  it('quem já entrou vai direto para o chat', async () => {
    render(<App authClient={fakeAuth(ALICE).client} initialPath="/" />)

    expect(await screen.findByRole('heading', { level: 1, name: 'Chat' })).toBeInTheDocument()
  })
})
