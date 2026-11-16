import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F04-01/02/03/05 contra `make dev` (emuladores + API local) e o Jira sandbox do PO.
// Credenciais do sandbox vêm do ambiente (JIRA_SANDBOX_* do .env.local); fora do CI.
const SITE = process.env.JIRA_SANDBOX_URL ?? ''
const EMAIL = process.env.JIRA_SANDBOX_EMAIL ?? ''
const TOKEN = process.env.JIRA_SANDBOX_API_TOKEN ?? ''

test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')
test.skip(!SITE || !EMAIL || !TOKEN, 'precisa de JIRA_SANDBOX_URL, _EMAIL e _API_TOKEN')

async function signIn(page: Page, request: Parameters<typeof createAccount>[0]) {
  const account = await createAccount(request, { verified: true, name: 'Pessoa Jira' })
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
  await page
    .getByRole('navigation', { name: 'Main' })
    .getByRole('link', { name: 'Settings' })
    .click()
}

async function fill(page: Page, site: string, token: string) {
  await page.getByLabel('Site URL').fill(site)
  await page.getByLabel('Atlassian account email').fill(EMAIL)
  await page.getByLabel('API token', { exact: true }).fill(token)
  await page.getByRole('button', { name: 'Validate and save' }).click()
}

test.describe('F04 conexão com o Jira sandbox', () => {
  test('F04-RF-03 AT-F04-02 AT-F04-03 recusa token inválido e URL fora do padrão', async ({
    page,
    request,
  }) => {
    await signIn(page, request)

    await fill(page, SITE, 'token-invalido-de-proposito')
    await expect(page.getByRole('alert')).toHaveText(
      'Jira rejected the credential. Check the email and token.',
    )

    await fill(page, 'http://169.254.169.254', TOKEN)
    // type="url" aceita http; quem recusa é a API (F04-RT-03).
    await expect(page.getByRole('alert')).toHaveText(
      'Enter a URL like https://<your-site>.atlassian.net',
    )
    await expect(page.getByText('Jira not connected')).toBeVisible()
  })

  test('F04-RF-01 F04-RF-02 F04-RF-04 F04-RF-05 AT-F04-01 AT-F04-05 conecta, mascara e remove', async ({
    page,
    request,
  }) => {
    await signIn(page, request)

    const listed = page.waitForResponse(
      (r) =>
        r.url().endsWith('/api/v1/jira/connections') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await fill(page, SITE, TOKEN)
    await expect(page.getByText(/^Connected as .+/)).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(`••••••••${TOKEN.slice(-4)}`)).toBeVisible()
    expect(await (await listed).text()).not.toContain(TOKEN)
    expect(await page.content()).not.toContain(TOKEN)

    await page.getByRole('button', { name: 'Test connection' }).click()
    await expect(page.getByText('Connection tested: Jira accepted the credential.')).toBeVisible()

    page.once('dialog', (dialog) => void dialog.accept())
    await page.getByRole('button', { name: 'Remove connection' }).click()
    await expect(page.getByRole('heading', { name: 'Connect Jira' })).toBeVisible()
    await page
      .getByRole('navigation', { name: 'Main' })
      .getByRole('link', { name: 'Jira projects' })
      .click()
    await expect(page.getByText('Connect your Jira account')).toBeVisible()
  })
})
