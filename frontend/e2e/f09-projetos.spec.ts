import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F09-01..03 contra `make dev` e o Jira sandbox do PO, só leitura (nada é escrito no Jira).
// Credenciais do sandbox vêm do ambiente (JIRA_SANDBOX_* do .env.local); fora do CI.
const SITE = process.env.JIRA_SANDBOX_URL ?? ''
const EMAIL = process.env.JIRA_SANDBOX_EMAIL ?? ''
const TOKEN = process.env.JIRA_SANDBOX_API_TOKEN ?? ''
const PROJECT = process.env.JIRA_SANDBOX_PROJECT_KEY ?? ''

test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')

async function signIn(page: Page, request: Parameters<typeof createAccount>[0]) {
  const account = await createAccount(request, { verified: true, name: 'Pessoa Projetos' })
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
}

const card = (page: Page, key: string) =>
  page.getByRole('listitem').filter({ has: page.getByText(new RegExp(`^${key} · `)) })

test.describe('F09 projetos Jira', () => {
  test('F09-RF-06 AT-F09-03 sem conexão orienta a conectar', async ({ page, request }) => {
    await signIn(page, request)
    await page
      .getByRole('navigation', { name: 'Main' })
      .getByRole('link', { name: 'Jira projects' })
      .click()

    await expect(page.getByText('Jira not connected').first()).toBeVisible()
    await expect(page.getByRole('link', { name: 'Connect Jira' })).toHaveAttribute(
      'href',
      '/settings',
    )
  })

  test.describe('com o Jira sandbox', () => {
    test.skip(!SITE || !EMAIL || !TOKEN || !PROJECT, 'precisa de JIRA_SANDBOX_*')

    test('F09-RF-01 F09-RF-02 F09-RF-03 F09-RF-04 F09-RF-05 AT-F09-01 AT-F09-02 lista, filtra e age', async ({
      page,
      request,
    }) => {
      await signIn(page, request)
      await page.goto('/settings')
      await page.getByLabel('Site URL').fill(SITE)
      await page.getByLabel('Atlassian account email').fill(EMAIL)
      await page.getByLabel('API token', { exact: true }).fill(TOKEN)
      await page.getByRole('button', { name: 'Validate and save' }).click()
      await expect(page.getByText(/Jira connected ·/)).toBeVisible({ timeout: 30_000 })

      await page.goto('/projects')
      const project = card(page, PROJECT)
      await expect(project).toBeVisible({ timeout: 30_000 })
      // Abertas e total são números do Jira (ou "—" se a contagem falhou).
      await expect(project.getByText(/open$/)).toHaveText(/^(\d+|—.*) open$/)
      await expect(project.getByText(/total$/)).toHaveText(/^(\d+|—.*) total$/)

      const search = page.getByLabel('Search by name or key')
      await search.fill(PROJECT.slice(0, 3).toLowerCase())
      await expect(project).toBeVisible()
      await search.fill('zzz-sem-projeto')
      await expect(page.getByText('No project matches “zzz-sem-projeto”.')).toBeVisible()
      await search.fill('')

      const jira = project.getByRole('link', { name: 'Open in Jira' })
      await expect(jira).toHaveAttribute('href', `${new URL(SITE).origin}/browse/${PROJECT}`)
      await expect(jira).toHaveAttribute('target', '_blank')
      await expect(jira).toHaveAttribute('rel', 'noopener noreferrer')

      await page.getByRole('button', { name: 'Refresh' }).click()
      await expect(page.getByRole('button', { name: 'Refresh' })).toBeEnabled({ timeout: 30_000 })
      await expect(project).toBeVisible()

      await project.getByRole('link', { name: 'Chat about this project' }).click()
      await expect(page).toHaveURL(new RegExp(`/chat\\?projeto=${PROJECT}$`))
      await expect(page.getByText(`Pinned project: ${PROJECT}`)).toBeVisible()
    })
  })
})
