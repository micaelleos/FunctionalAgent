import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from '../App'
import { ALICE, fakeAuth } from '../test/fakeAuth'
import { safeRedirect } from './redirect'

const renderAt = (path: string, auth = fakeAuth()) => {
  render(<App authClient={auth.client} initialPath={path} />)
  return auth
}

describe('F03-RF-04 rotas protegidas', () => {
  it.each(['/chat', '/account', '/qualquer'])('sem login, %s leva para o login', async (path) => {
    renderAt(path)

    expect(
      await screen.findByRole('heading', { name: 'Sign in to SpecFlow AI' }),
    ).toBeInTheDocument()
  })

  it('"Privacy" é pública', async () => {
    renderAt('/privacy')

    expect(await screen.findByRole('heading', { level: 1, name: 'Privacy' })).toBeInTheDocument()
  })

  it('conta de e-mail não confirmada vai para a verificação', async () => {
    renderAt('/chat', fakeAuth({ ...ALICE, emailVerified: false }))

    expect(await screen.findByRole('heading', { name: 'Confirm your email' })).toBeInTheDocument()
  })

  it('quem já entrou e abre o login segue para o chat', async () => {
    renderAt('/login', fakeAuth(ALICE))

    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })

  it('só redireciona para caminhos internos', () => {
    expect(safeRedirect('/account')).toBe('/account')
    expect(safeRedirect('//evil.com')).toBe('/chat')
    expect(safeRedirect('https://evil.com')).toBe('/chat')
    expect(safeRedirect(undefined)).toBe('/chat')
  })
})

describe('F03-RF-02 F03-RF-01 login', () => {
  it('entra com e-mail e senha e volta para a página pedida', async () => {
    const auth = renderAt('/account')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Email'), 'alice@teste.dev')
    await user.type(screen.getByLabelText('Password'), 'segredo1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(auth.client.signInWithEmail).toHaveBeenCalledWith('alice@teste.dev', 'segredo1')
    expect(await screen.findByRole('heading', { name: 'My account' })).toBeInTheDocument()
  })

  it('mostra erro em português quando a senha está errada', async () => {
    const auth = fakeAuth()
    auth.client.signInWithEmail.mockRejectedValueOnce({ code: 'auth/invalid-credential' })
    renderAt('/login', auth)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Email'), 'alice@teste.dev')
    await user.type(screen.getByLabelText('Password'), 'errada')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.')
  })

  it('entra com Google', async () => {
    const auth = renderAt('/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Sign in with Google' }))

    expect(auth.client.signInWithGoogle).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })
})

describe('F03-RF-02 cadastro e verificação de e-mail', () => {
  it('cadastra e pede a confirmação do e-mail', async () => {
    const auth = renderAt('/signup')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Name'), 'Nova Pessoa')
    await user.type(screen.getByLabelText('Email'), 'nova@teste.dev')
    await user.type(screen.getByLabelText(/Password/), 'segredo1')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(auth.client.signUp).toHaveBeenCalledWith('Nova Pessoa', 'nova@teste.dev', 'segredo1')
    expect(await screen.findByText(/confirmation link to nova@teste.dev/)).toBeInTheDocument()
  })

  it(`"I've confirmed" sem confirmar mostra aviso; depois de confirmar, entra`, async () => {
    const auth = renderAt('/verify-email', fakeAuth({ ...ALICE, emailVerified: false }))
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: "I've confirmed" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("We haven't seen the confirmation")

    auth.client.reload.mockResolvedValueOnce(ALICE)
    await user.click(screen.getByRole('button', { name: "I've confirmed" }))
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })

  it('reenvia o e-mail de confirmação', async () => {
    const auth = renderAt('/verify-email', fakeAuth({ ...ALICE, emailVerified: false }))

    await userEvent.click(await screen.findByRole('button', { name: 'Resend email' }))

    expect(auth.client.resendVerification).toHaveBeenCalled()
    expect(await screen.findByRole('status')).toHaveTextContent('Email sent again')
  })
})

describe('F03-RF-03 redefinir senha', () => {
  it('envia o link sem revelar se a conta existe', async () => {
    const auth = fakeAuth()
    auth.client.sendPasswordReset.mockRejectedValueOnce({ code: 'auth/user-not-found' })
    renderAt('/reset-password', auth)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Email'), 'ninguem@teste.dev')
    await user.click(screen.getByRole('button', { name: 'Send link' }))

    expect(await screen.findByRole('status')).toHaveTextContent("If there's an account")
  })
})

describe('F03-RF-06 sair', () => {
  it.each(['/chat', '/account', '/privacy'])('sai a partir de %s', async (path) => {
    const auth = renderAt(path, fakeAuth(ALICE))

    expect(await screen.findByRole('link', { name: 'Alice' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    await waitFor(() => expect(auth.current()).toBeNull())
    expect(
      await screen.findByRole('heading', { name: 'Sign in to SpecFlow AI' }),
    ).toBeInTheDocument()
  })
})
