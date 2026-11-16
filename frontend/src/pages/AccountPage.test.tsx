import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { ALICE, fakeAuth } from '../test/fakeAuth'
import { api, server } from '../test/server'

afterEach(() => vi.restoreAllMocks())

const renderAccount = () => {
  const auth = fakeAuth(ALICE)
  render(<App authClient={auth.client} initialPath="/account" />)
  return auth
}

describe('F03-RF-05 perfil', () => {
  it('mostra o perfil vindo de GET /api/v1/me', async () => {
    renderAccount()

    expect(await screen.findByText('alice@teste.dev')).toBeInTheDocument()
    expect(screen.getByText('11/14/2026')).toBeInTheDocument()
  })

  it('mostra erro da API em português', async () => {
    server.use(
      http.get(api('/api/v1/me'), () =>
        HttpResponse.json({ code: 'email-not-verified' }, { status: 403 }),
      ),
    )
    renderAccount()

    expect(await screen.findByRole('alert')).toHaveTextContent('Confirm your email')
  })
})

describe('F03-RF-07 exportar', () => {
  it('baixa o JSON dos meus dados', async () => {
    const createObjectURL = vi.fn(() => 'blob:x')
    Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    renderAccount()

    await userEvent.click(await screen.findByRole('button', { name: 'Download my data' }))

    await waitFor(() => expect(click).toHaveBeenCalled())
    expect(createObjectURL).toHaveBeenCalled()
  })
})

describe('F03-RF-08 excluir conta', () => {
  it('só exclui depois de digitar EXCLUIR e então desloga', async () => {
    let deleted = false
    server.use(
      http.delete(api('/api/v1/me'), () => {
        deleted = true
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const auth = renderAccount()
    const user = userEvent.setup()

    const button = await screen.findByRole('button', { name: 'Delete my data' })
    expect(button).toBeDisabled()
    expect(screen.getByText(/shared with the other apps in this portfolio/)).toBeInTheDocument()

    await user.type(screen.getByLabelText('Type DELETE to confirm'), 'excluir')
    expect(button).toBeDisabled()
    await user.clear(screen.getByLabelText('Type DELETE to confirm'))
    await user.type(screen.getByLabelText('Type DELETE to confirm'), 'DELETE')
    await user.click(button)

    await waitFor(() => expect(deleted).toBe(true))
    await waitFor(() => expect(auth.current()).toBeNull())
    expect(
      await screen.findByRole('heading', { name: 'Sign in to SpecFlow AI' }),
    ).toBeInTheDocument()
  })
})
