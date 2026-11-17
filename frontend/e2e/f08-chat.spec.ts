import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F08-01/03/05/06 contra `make dev` com LLM_PROVIDER=fake (o modelo de eco repete a mensagem):
// o caminho real front → SSE → API → Firestore, sem Vertex e sem escrever no Jira.
// AT-F08-02 (ferramenta e cartão) e AT-F08-04 (parar) precisam do modelo real; ficam na
// aceitação com o Gemini (evidências na spec) e nos testes de componente.
test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')
test.skip(process.env.E2E_REAL_LLM === '1', 'as respostas conferidas aqui são do modelo de eco')

const MARKDOWN =
  'Resumo com **negrito** e tabela:\n\n| CA | Tipo |\n|---|---|\n| CA-01 | principal |'

async function signIn(page: Page, request: Parameters<typeof createAccount>[0]) {
  const account = await createAccount(request, { verified: true, name: 'Pessoa Chat' })
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
}

async function send(page: Page, text: string) {
  const box = page.getByLabel('Message')
  await box.fill(text)
  await box.press('Enter')
}

async function serious(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.help}`)
}

const sidebar = (page: Page) => page.getByRole('complementary', { name: 'Conversations' })

test.describe('F08 chat', () => {
  test('F08-RF-01 F08-RF-02 AT-F08-01 envia, recebe em Markdown e o histórico volta ao recarregar', async ({
    page,
    request,
  }) => {
    await signIn(page, request)

    await send(page, MARKDOWN)

    await expect(page).toHaveURL(/\/chat\/[\w-]+$/)
    const reply = page.locator('.chat-markdown').last()
    await expect(reply.getByText('negrito')).toHaveJSProperty('tagName', 'STRONG')
    await expect(reply.getByRole('cell', { name: 'CA-01' })).toBeVisible()
    await expect(page.getByLabel('Message')).toHaveValue('')
    await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
    await expect(sidebar(page).getByRole('listitem')).toHaveCount(1)

    await page.reload()
    await expect(page.locator('.chat-markdown').getByRole('cell', { name: 'CA-01' })).toBeVisible()
    await expect(page.getByText('Resumo com **negrito**')).toBeVisible() // a mensagem do usuário, crua
  })

  test('F08-RF-05 AT-F08-03 renomeia e exclui pela lateral', async ({ page, request }) => {
    await signIn(page, request)
    await send(page, 'Primeira conversa')
    await expect(page).toHaveURL(/\/chat\/[\w-]+$/)
    const link = sidebar(page).getByRole('listitem')
    await expect(link).toHaveCount(1)
    const title = (await link.locator('a span').first().textContent()) ?? ''

    await sidebar(page)
      .getByRole('button', { name: `Rename “${title}”` })
      .click()
    await page.getByLabel('New title').fill('Checkout Pix')
    await page.getByLabel('New title').press('Enter')
    await expect(sidebar(page).getByText('Checkout Pix')).toBeVisible()
    await page.reload()
    await expect(sidebar(page).getByText('Checkout Pix')).toBeVisible()

    page.once('dialog', (dialog) => void dialog.accept())
    await sidebar(page).getByRole('button', { name: 'Delete “Checkout Pix”' }).click()
    await expect(page).toHaveURL(/\/chat$/)
    await expect(sidebar(page).getByText('Your conversations show up here.')).toBeVisible()
    await page.reload()
    await expect(sidebar(page).getByRole('link', { name: /Checkout Pix/ })).toHaveCount(0)
  })

  test('F08-RF-07 AT-F08-05 sem rede o texto fica no campo e "Try again" envia', async ({
    page,
    request,
  }) => {
    await signIn(page, request)
    await page.route('**/api/v1/conversations/*/messages', (route) =>
      route.request().method() === 'POST' ? route.abort('internetdisconnected') : route.continue(),
    )

    await send(page, 'Mensagem que não saiu')

    await expect(page.getByRole('alert')).toContainText("We couldn't reach the server")
    await expect(page.getByLabel('Message')).toHaveValue('Mensagem que não saiu')

    await page.unroute('**/api/v1/conversations/*/messages')
    await page.getByRole('button', { name: 'Try again' }).click()
    await expect(page.locator('.chat-markdown').last()).toContainText('Mensagem que não saiu')
    await expect(page.getByLabel('Message')).toHaveValue('')
  })

  test('F08-RF-09 F08-RT-04 AT-F08-06 celular sem rolagem lateral e sem violações', async ({
    page,
    request,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await signIn(page, request)
    await send(page, MARKDOWN)
    await expect(page.locator('.chat-markdown').last().getByRole('table')).toBeVisible()
    expect(await serious(page), 'desktop').toEqual([])

    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('button', { name: 'Show conversations' }).click()
    await expect(sidebar(page).getByRole('listitem')).toHaveCount(1)
    expect(await serious(page), 'celular').toEqual([])
    const overflow = await page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    expect(overflow).toBe(false)
  })
})
