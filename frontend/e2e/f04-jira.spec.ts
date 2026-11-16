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
  await page.getByLabel('E-mail').fill(account.email)
  await page.getByLabel('Senha').fill(account.password)
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
  await page
    .getByRole('navigation', { name: 'Principal' })
    .getByRole('link', { name: 'Configurações' })
    .click()
}

async function fill(page: Page, site: string, token: string) {
  await page.getByLabel('URL do site').fill(site)
  await page.getByLabel('E-mail da conta Atlassian').fill(EMAIL)
  await page.getByLabel('Token de API').fill(token)
  await page.getByRole('button', { name: 'Validar e salvar' }).click()
}

test.describe('F04 conexão com o Jira sandbox', () => {
  test('F04-RF-03 AT-F04-02 AT-F04-03 recusa token inválido e URL fora do padrão', async ({
    page,
    request,
  }) => {
    await signIn(page, request)

    await fill(page, SITE, 'token-invalido-de-proposito')
    await expect(page.getByRole('alert')).toHaveText(
      'O Jira recusou a credencial. Verifique e-mail e token.',
    )

    await fill(page, 'http://169.254.169.254', TOKEN)
    // type="url" aceita http; quem recusa é a API (F04-RT-03).
    await expect(page.getByRole('alert')).toHaveText(
      'Informe uma URL https://<seu-site>.atlassian.net',
    )
    await expect(page.getByText('Jira não conectado')).toBeVisible()
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
    await expect(page.getByText(/^Conectado como .+/)).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(`••••••••${TOKEN.slice(-4)}`)).toBeVisible()
    expect(await (await listed).text()).not.toContain(TOKEN)
    expect(await page.content()).not.toContain(TOKEN)

    await page.getByRole('button', { name: 'Testar conexão' }).click()
    await expect(page.getByText('Conexão testada: o Jira aceitou a credencial.')).toBeVisible()

    page.once('dialog', (dialog) => void dialog.accept())
    await page.getByRole('button', { name: 'Remover conexão' }).click()
    await expect(page.getByRole('heading', { name: 'Conectar o Jira' })).toBeVisible()
    await page
      .getByRole('navigation', { name: 'Principal' })
      .getByRole('link', { name: 'Projetos Jira' })
      .click()
    await expect(page.getByText('Conecte sua conta do Jira')).toBeVisible()
  })
})
