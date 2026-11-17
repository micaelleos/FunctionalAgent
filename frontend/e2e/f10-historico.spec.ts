import { type Browser, expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F10-01..04 contra `make dev` com o modelo real e o Jira sandbox do PO.
// ESCREVE NO JIRA: confirma a criação de 1 issue. Só roda com E2E_JIRA_WRITE=1, que o PO autoriza.
const SITE = process.env.JIRA_SANDBOX_URL ?? ''
const EMAIL = process.env.JIRA_SANDBOX_EMAIL ?? ''
const TOKEN = process.env.JIRA_SANDBOX_API_TOKEN ?? ''
const PROJECT = process.env.JIRA_SANDBOX_PROJECT_KEY ?? ''

test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')

type Account = Awaited<ReturnType<typeof createAccount>>

async function signIn(page: Page, account: Account) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
}

test.describe('F10 histórico de issues', () => {
  test('F10-RF-01 sem issues mostra o estado vazio', async ({ page, request }) => {
    await signIn(page, await createAccount(request, { verified: true, name: 'Pessoa Vazia' }))
    await page
      .getByRole('navigation', { name: 'Main' })
      .getByRole('link', { name: 'Created issues' })
      .click()
    await expect(page.getByText(/No issues yet/)).toBeVisible()
  })

  test.describe('com o agente real e o Jira sandbox', () => {
    test.skip(process.env.E2E_REAL_LLM !== '1', 'precisa do modelo real: E2E_REAL_LLM=1')
    test.skip(process.env.E2E_JIRA_WRITE !== '1', 'escreve no Jira: E2E_JIRA_WRITE=1')
    test.skip(!SITE || !EMAIL || !TOKEN || !PROJECT, 'precisa de JIRA_SANDBOX_*')
    test.setTimeout(240_000)

    test('F10-RF-01 F10-RF-02 F10-RF-03 F10-RF-04 F10-RF-05 F10-RF-06 F10-RF-07 AT-F10-01 AT-F10-02 AT-F10-03 AT-F10-04', async ({
      page,
      request,
      browser,
    }) => {
      const account = await createAccount(request, { verified: true, name: 'Pessoa Histórico' })
      await signIn(page, account)
      await page.goto('/settings')
      await page.getByLabel('Site URL').fill(SITE)
      await page.getByLabel('Atlassian account email').fill(EMAIL)
      await page.getByLabel('API token', { exact: true }).fill(TOKEN)
      await page.getByRole('button', { name: 'Validate and save' }).click()
      await expect(page.getByText(/Jira connected ·/)).toBeVisible({ timeout: 30_000 })

      await page.goto(`/chat?projeto=${PROJECT}`)
      await page
        .getByLabel('Message')
        .fill(
          'Crie uma story: como cliente, quero ver o prazo de entrega estimado na página do ' +
            'produto, calculado pelo CEP informado. Critérios: com CEP válido mostra "Chega em N ' +
            'dias úteis"; CEP inválido mostra "CEP inválido"; sem CEP, nada aparece. Fora do ' +
            'escopo: frete grátis. Está completo, pode propor sem perguntar mais nada.',
        )
      await page.getByLabel('Message').press('Enter')
      const card = page.getByRole('region', { name: new RegExp(`in ${PROJECT}$`) }).first()
      await card.getByRole('button', { name: 'Confirm and create' }).click({ timeout: 150_000 })
      const created = card.getByText(/^Created as /)
      await expect(created).toBeVisible({ timeout: 60_000 })
      const key = ((await created.textContent()) ?? '').replace('Created as ', '').trim()
      expect(key).toMatch(new RegExp(`^${PROJECT}-\\d+$`))
      const conversationUrl = new URL(page.url()).pathname

      // AT-F10-01: outra sessão da mesma conta vê a issue no topo.
      const other = await secondSession(browser, account)
      await other.goto('/issues')
      const link = other.getByRole('link', { name: key, exact: true })
      await expect(link).toBeVisible({ timeout: 30_000 })
      const firstRow = other.getByRole('row').nth(1)
      await expect(firstRow.getByRole('link', { name: key, exact: true })).toBeVisible()
      await expect(firstRow).toContainText('Story')
      await expect(link).toHaveAttribute('href', `${new URL(SITE).origin}/browse/${key}`)

      // AT-F10-02: filtros por projeto e tipo no servidor.
      await other.getByLabel('Project').selectOption(PROJECT)
      await other.getByRole('button', { name: 'Story', exact: true }).click()
      await expect(link).toBeVisible()
      await other.getByRole('button', { name: 'Epic', exact: true }).click()
      await expect(other.getByText('No issues match these filters.')).toBeVisible()
      await other.getByRole('button', { name: 'All', exact: true }).click()
      await expect(link).toBeVisible()

      // AT-F10-03: status atual no Jira (o nome vem no idioma do site).
      const row = other.getByRole('row').filter({ has: link })
      await other.getByRole('button', { name: 'Refresh Jira status' }).click()
      await expect(row.locator('td').nth(4)).not.toHaveText('—', { timeout: 30_000 })
      await expect(row.locator('td').nth(4)).not.toHaveText('Not found in Jira')

      // AT-F10-04: selo e "Copiar para agente de código".
      await expect(row.getByText(/^(Agent-ready|Not ready)$/)).toBeVisible()
      await row.getByRole('button', { name: `Copy ${key} for a coding agent` }).click()
      await expect(other.getByText(`${key} copied. Paste it into your coding agent.`)).toBeVisible()
      const copied = String(await other.evaluate('navigator.clipboard.readText()'))
      expect(copied).toContain(`Implemente a issue ${key} abaixo.`)
      expect(copied).toContain('## Critérios de aceite')

      // A origem abre a conversa.
      await row.getByRole('link').last().click()
      await expect(other).toHaveURL(new RegExp(`${conversationUrl}$`))
      await other.context().close()
    })
  })
})

async function secondSession(browser: Browser, account: Account): Promise<Page> {
  const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] })
  const page = await context.newPage()
  await signIn(page, account)
  return page
}
