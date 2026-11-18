import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from '../App'
import { fakeAuth } from '../test/fakeAuth'

describe('F12-RF-04 AT-F12-03 página de privacidade', () => {
  it('é pública e diz o que guardamos, com quem, o que vai para os logs e como apagar', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/privacy" />)

    expect(await screen.findByRole('heading', { level: 1, name: 'Privacy' })).toBeInTheDocument()
    for (const section of ['What we keep', 'Who processes it', 'Logs and errors', 'Your choices']) {
      expect(screen.getByRole('heading', { level: 2, name: section })).toBeInTheDocument()
    }
    expect(screen.getByText(/encrypted with a Google Cloud KMS key/)).toBeInTheDocument()
    expect(screen.getByText(/never include message content or your Jira token/)).toBeInTheDocument()
    expect(screen.getByText(/Delete my data erases all of it/)).toBeInTheDocument()
  })

  it('o cadastro e a página inicial têm o link', async () => {
    const { unmount } = render(<App authClient={fakeAuth().client} initialPath="/signup" />)
    expect(await screen.findByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
    unmount()

    render(<App authClient={fakeAuth().client} initialPath="/" />)
    expect(await screen.findByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
  })
})
