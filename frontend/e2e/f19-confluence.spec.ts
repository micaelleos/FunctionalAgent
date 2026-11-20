import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F19-01 contra `make dev` (CONFLUENCE_ENABLED=true) e o sandbox do PO: só leitura no
// Confluence; o vínculo é gravado no Firestore do emulador. Projeto e espaço com a mesma chave.
const SITE = process.env.JIRA_SANDBOX_URL ?? ''
const EMAIL = process.env.JIRA_SANDBOX_EMAIL ?? ''
const TOKEN = process.env.JIRA_SANDBOX_API_TOKEN ?? ''
const PROJECT = process.env.JIRA_SANDBOX_PROJECT_KEY ?? ''

test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')
test.skip(!SITE || !EMAIL || !TOKEN || !PROJECT, 'precisa de JIRA_SANDBOX_*')

async function signIn(page: Page, request: Parameters<typeof createAccount>[0]) {
  const account = await createAccount(request, { verified: true, name: 'Pessoa Docs' })
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
}

const card = (page: Page, key: string) =>
  page.getByRole('listitem').filter({ has: page.getByText(new RegExp(`^${key} · `)) })

test('F19-RF-01 F19-RF-02 AT-F19-01 vínculo automático pela chave do projeto', async ({
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
  await project.getByRole('button', { name: 'Project docs' }).click()

  await expect(project.getByText('Found a space with the same key:')).toBeVisible({
    timeout: 30_000,
  })
  const space = project.getByRole('link', { name: new RegExp(`\\(${PROJECT}\\)$`) })
  await expect(space).toHaveAttribute('href', new RegExp(`/wiki/spaces/${PROJECT}`))

  await project.getByRole('button', { name: 'Link', exact: true }).click()
  await expect(
    project.getByText('The agent reads this space before proposing issues:'),
  ).toBeVisible()

  // O vínculo persiste: recarregar mostra o espaço vinculado, não a sugestão.
  await page.reload()
  await card(page, PROJECT).getByRole('button', { name: 'Project docs' }).click()
  await expect(
    card(page, PROJECT).getByText('The agent reads this space before proposing issues:'),
  ).toBeVisible({ timeout: 30_000 })
  await card(page, PROJECT).getByRole('button', { name: 'Unlink' }).click()
  await expect(card(page, PROJECT).getByText('Found a space with the same key:')).toBeVisible({
    timeout: 30_000,
  })
})
