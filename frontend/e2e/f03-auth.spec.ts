import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

import {
  API,
  confirmEmail,
  createAccount,
  EMULATORS,
  randomEmail,
  userDocStatus,
} from './emulators'

// AT-F03-01..04 contra `make dev` (emuladores de Auth e Firestore). Em produção, só o roteiro manual
// M-F03-01/02 (decisão do PO: nada de contas de teste no Auth compartilhado).
test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')

async function signIn(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
}

test.describe('F03 autenticação e conta', () => {
  test('AT-F03-01 F03-RF-04 acesso sem login é redirecionado', async ({ page }) => {
    await page.goto('/chat')

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: 'Sign in to SpecFlow AI' })).toBeVisible()
  })

  test('AT-F03-02 F03-RF-02 F03-RF-05 F03-RF-06 cadastro e login por e-mail', async ({
    page,
    request,
  }) => {
    const email = randomEmail()
    await page.goto('/signup')
    await page.getByLabel('Name').fill('Pessoa E2E')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel(/Password/).fill('senha-e2e-123')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page.getByText(`confirmation link to ${email}`)).toBeVisible()

    await confirmEmail(request, email)
    await page.getByRole('button', { name: "I've confirmed" }).click()
    await expect(page.getByRole('link', { name: 'Pessoa E2E' })).toBeVisible()

    await page.getByRole('link', { name: 'Pessoa E2E' }).click()
    await expect(page.getByText(email)).toBeVisible() // vem de GET /api/v1/me

    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await signIn(page, email, 'senha-e2e-123')
    await expect(page.getByRole('link', { name: 'Pessoa E2E' })).toBeVisible()
  })

  test('AT-F03-03 F03-RT-01 F03-RT-02 F03-RT-07 API recusa chamadas sem identidade válida', async ({
    request,
  }) => {
    const anonymous = await request.get(`${API}/api/v1/me`)
    expect(anonymous.status()).toBe(401)
    expect(anonymous.headers()['content-type']).toBe('application/problem+json')

    const unverified = await createAccount(request, { verified: false })
    const blocked = await request.get(`${API}/api/v1/me`, {
      headers: { Authorization: `Bearer ${unverified.token}` },
    })
    expect(blocked.status()).toBe(403)

    const a = await createAccount(request, { verified: true })
    const b = await createAccount(request, { verified: true })
    const me = await request.get(`${API}/api/v1/me?uid=${b.uid}`, {
      headers: { Authorization: `Bearer ${a.token}` },
    })
    expect(((await me.json()) as { uid: string }).uid).toBe(a.uid)
  })

  test('AT-F03-04 F03-RF-07 F03-RF-08 exportar e excluir conta', async ({ page, request }) => {
    const account = await createAccount(request, { verified: true, name: 'Pessoa Export' })
    await signIn(page, account.email, account.password)
    await page.getByRole('link', { name: 'Pessoa Export' }).click()
    await expect(page.getByText(account.email)).toBeVisible()
    expect(await userDocStatus(request, account.uid)).toBe(200)

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Download my data' }).click(),
    ])
    const exported = JSON.parse(await readFile((await download.path())!, 'utf-8')) as {
      user: { data: { email: string } }
    }
    expect(exported.user.data.email).toBe(account.email)

    await page.getByLabel('Type DELETE to confirm').fill('DELETE')
    await page.getByRole('button', { name: 'Delete my data' }).click()
    await expect(page).toHaveURL(/\/login$/)
    expect(await userDocStatus(request, account.uid)).toBe(404)

    // O login do portfólio continua: entrar de novo começa com um perfil novo.
    await signIn(page, account.email, account.password)
    await page.getByRole('link', { name: 'Pessoa Export' }).click()
    await expect(page.getByText(account.email)).toBeVisible()
    expect(await userDocStatus(request, account.uid)).toBe(200)
  })

  for (const path of ['/login', '/signup', '/reset-password']) {
    test(`F03-RT-06 ${path} sem violações sérias de acessibilidade`, async ({ page }) => {
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

      const { violations } = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()
      const serious = violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
      expect(serious.map((v) => `${v.id}: ${v.help}`)).toEqual([])
    })
  }
})
