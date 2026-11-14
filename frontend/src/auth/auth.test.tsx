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
  it.each(['/chat', '/conta', '/qualquer'])('sem login, %s leva para o login', async (path) => {
    renderAt(path)

    expect(
      await screen.findByRole('heading', { name: 'Entrar no SpecFlow AI' }),
    ).toBeInTheDocument()
  })

  it('"Sobre" é público', async () => {
    renderAt('/sobre')

    expect(await screen.findByRole('heading', { name: 'SpecFlow AI' })).toBeInTheDocument()
  })

  it('conta de e-mail não confirmada vai para a verificação', async () => {
    renderAt('/chat', fakeAuth({ ...ALICE, emailVerified: false }))

    expect(await screen.findByRole('heading', { name: 'Confirme seu e-mail' })).toBeInTheDocument()
  })

  it('quem já entrou e abre o login segue para o chat', async () => {
    renderAt('/login', fakeAuth(ALICE))

    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })

  it('só redireciona para caminhos internos', () => {
    expect(safeRedirect('/conta')).toBe('/conta')
    expect(safeRedirect('//evil.com')).toBe('/chat')
    expect(safeRedirect('https://evil.com')).toBe('/chat')
    expect(safeRedirect(undefined)).toBe('/chat')
  })
})

describe('F03-RF-02 F03-RF-01 login', () => {
  it('entra com e-mail e senha e volta para a página pedida', async () => {
    const auth = renderAt('/conta')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('E-mail'), 'alice@teste.dev')
    await user.type(screen.getByLabelText('Senha'), 'segredo1')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(auth.client.signInWithEmail).toHaveBeenCalledWith('alice@teste.dev', 'segredo1')
    expect(await screen.findByRole('heading', { name: 'Minha conta' })).toBeInTheDocument()
  })

  it('mostra erro em português quando a senha está errada', async () => {
    const auth = fakeAuth()
    auth.client.signInWithEmail.mockRejectedValueOnce({ code: 'auth/invalid-credential' })
    renderAt('/login', auth)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('E-mail'), 'alice@teste.dev')
    await user.type(screen.getByLabelText('Senha'), 'errada')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos.')
  })

  it('entra com Google', async () => {
    const auth = renderAt('/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Entrar com Google' }))

    expect(auth.client.signInWithGoogle).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })
})

describe('F03-RF-02 cadastro e verificação de e-mail', () => {
  it('cadastra e pede a confirmação do e-mail', async () => {
    const auth = renderAt('/cadastro')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Nome'), 'Nova Pessoa')
    await user.type(screen.getByLabelText('E-mail'), 'nova@teste.dev')
    await user.type(screen.getByLabelText(/Senha/), 'segredo1')
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(auth.client.signUp).toHaveBeenCalledWith('Nova Pessoa', 'nova@teste.dev', 'segredo1')
    expect(await screen.findByText(/link de confirmação para nova@teste.dev/)).toBeInTheDocument()
  })

  it('"Já confirmei" sem confirmar mostra aviso; depois de confirmar, entra', async () => {
    const auth = renderAt('/verificar-email', fakeAuth({ ...ALICE, emailVerified: false }))
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Já confirmei' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Ainda não encontramos')

    auth.client.reload.mockResolvedValueOnce(ALICE)
    await user.click(screen.getByRole('button', { name: 'Já confirmei' }))
    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
  })

  it('reenvia o e-mail de confirmação', async () => {
    const auth = renderAt('/verificar-email', fakeAuth({ ...ALICE, emailVerified: false }))

    await userEvent.click(await screen.findByRole('button', { name: 'Reenviar e-mail' }))

    expect(auth.client.resendVerification).toHaveBeenCalled()
    expect(await screen.findByRole('status')).toHaveTextContent('E-mail reenviado')
  })
})

describe('F03-RF-03 redefinir senha', () => {
  it('envia o link sem revelar se a conta existe', async () => {
    const auth = fakeAuth()
    auth.client.sendPasswordReset.mockRejectedValueOnce({ code: 'auth/user-not-found' })
    renderAt('/recuperar-senha', auth)
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('E-mail'), 'ninguem@teste.dev')
    await user.click(screen.getByRole('button', { name: 'Enviar link' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Se houver uma conta')
  })
})

describe('F03-RF-06 sair', () => {
  it.each(['/chat', '/conta', '/sobre'])('sai a partir de %s', async (path) => {
    const auth = renderAt(path, fakeAuth(ALICE))

    expect(await screen.findByRole('link', { name: 'Alice' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Sair' }))

    await waitFor(() => expect(auth.current()).toBeNull())
    expect(
      await screen.findByRole('heading', { name: 'Entrar no SpecFlow AI' }),
    ).toBeInTheDocument()
  })
})
