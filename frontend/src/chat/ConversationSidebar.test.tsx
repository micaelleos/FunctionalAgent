import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { ApiError } from '../lib/api'
import { createDemoProductApi } from '../product/demo'
import type { ProductApi } from '../product/types'
import { ALICE, fakeAuth } from '../test/fakeAuth'

afterEach(() => vi.restoreAllMocks())

const NOW = Date.parse('2026-11-17T12:00:00Z')

function renderApp(path: string, productApi: ProductApi) {
  render(<App authClient={fakeAuth(ALICE).client} productApi={productApi} initialPath={path} />)
}

const sidebar = () => screen.getByRole('complementary', { name: 'Conversations' })

describe('F08-RF-05 conversas na lateral', () => {
  it('renomear muda o título na hora', async () => {
    const api = createDemoProductApi(() => NOW)
    let release: () => void = () => undefined
    const rename = api.renameConversation
    api.renameConversation = vi.fn(async (id, title) => {
      await new Promise<void>((resolve) => (release = resolve))
      return rename(id, title)
    })
    renderApp('/chat/c1', api)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Rename “Pix checkout”' }))
    const input = screen.getByLabelText('New title')
    await user.clear(input)
    await user.type(input, 'Teste UI{Enter}')

    // Otimista: aparece antes de a API responder.
    expect(within(sidebar()).getByText('Teste UI')).toBeInTheDocument()
    release()
    await waitFor(() => expect(api.renameConversation).toHaveBeenCalledWith('c1', 'Teste UI'))
    expect(await within(sidebar()).findByText('Teste UI')).toBeInTheDocument()
  })

  it('se a API recusar, o título volta e o erro aparece', async () => {
    const api = createDemoProductApi(() => NOW)
    api.renameConversation = vi
      .fn()
      .mockRejectedValue(new ApiError(404, 'conversation-not-found', 'x'))
    renderApp('/chat/c1', api)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Rename “Pix checkout”' }))
    await user.clear(screen.getByLabelText('New title'))
    await user.type(screen.getByLabelText('New title'), 'Outro{Enter}')

    expect(await within(sidebar()).findByRole('alert')).toHaveTextContent(
      'This conversation no longer exists.',
    )
    expect(within(sidebar()).getByText('Pix checkout')).toBeInTheDocument()
    expect(within(sidebar()).queryByText('Outro')).not.toBeInTheDocument()
  })

  it('Escape cancela a edição sem chamar a API', async () => {
    const api = createDemoProductApi(() => NOW)
    const rename = vi.spyOn(api, 'renameConversation')
    renderApp('/chat/c1', api)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Rename “Pix checkout”' }))
    await user.type(screen.getByLabelText('New title'), ' mudado{Escape}')

    expect(rename).not.toHaveBeenCalled()
    expect(within(sidebar()).getByText('Pix checkout')).toBeInTheDocument()
  })

  it('excluir pede confirmação, some da lista e volta para uma conversa nova', async () => {
    const api = createDemoProductApi(() => NOW)
    const remove = vi.spyOn(api, 'deleteConversation')
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderApp('/chat/c1', api)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Delete “Pix checkout”' }))

    expect(confirm).toHaveBeenCalledWith(
      expect.stringContaining('Issues already created stay in Jira'),
    )
    await waitFor(() => expect(remove).toHaveBeenCalledWith('c1'))
    expect(within(sidebar()).queryByText('Pix checkout')).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { level: 1, name: 'Chat' })).toBeInTheDocument()
  })

  it('cancelar a confirmação não exclui', async () => {
    const api = createDemoProductApi(() => NOW)
    const remove = vi.spyOn(api, 'deleteConversation')
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderApp('/chat/c1', api)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Delete “Pix checkout”' }))

    expect(remove).not.toHaveBeenCalled()
    expect(within(sidebar()).getByText('Pix checkout')).toBeInTheDocument()
  })

  it('F08-RF-09 no celular a lista fica atrás de um botão', async () => {
    renderApp(
      '/chat',
      createDemoProductApi(() => NOW),
    )
    const user = userEvent.setup()
    const toggle = await screen.findByRole('button', { name: 'Show conversations' })

    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await user.click(toggle)
    expect(screen.getByRole('button', { name: 'Hide conversations' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })
})
