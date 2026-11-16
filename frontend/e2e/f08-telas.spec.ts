import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// Telas principais (F08-RF-10) contra `make dev`, sem dados de demonstração: o que vai para
// produção. Cada tela abre pelo menu, mostra o estado vazio e passa no axe (F08-RT-04).
test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')

const SCREENS = [
  ['Chat', '/chat', 'Chat'],
  ['Jira projects', '/projects', 'Jira projects'],
  ['Created issues', '/issues', 'Created issues'],
  ['Settings', '/settings', 'Settings'],
  ['My account', '/account', 'My account'],
] as const

async function serious(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.help}`)
}

test.describe('F08 telas principais', () => {
  test('F08-RF-11 F08-RT-04 página inicial pública sem violações', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1, name: /coding agent can actually ship/ })).toBeVisible()
    expect(await serious(page)).toEqual([])
    await page.getByRole('link', { name: 'Get started free' }).click()
    await expect(page).toHaveURL(/\/signup$/)
  })

  test('F08-RF-10 F08-RT-04 F08-RT-08 menu leva a cada tela, sem dados inventados e sem violações', async ({
    page,
    request,
  }) => {
    const account = await createAccount(request, { verified: true, name: 'Pessoa Telas' })
    await page.goto('/login')
    await page.getByLabel('Email').fill(account.email)
    await page.getByLabel('Password').fill(account.password)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
    await expect(page.getByText('Demo data')).toHaveCount(0)

    const nav = page.getByRole('navigation', { name: 'Main' })
    for (const [link, path, heading] of SCREENS) {
      await nav.getByRole('link', { name: link, exact: true }).click()
      await expect(page).toHaveURL(new RegExp(`${path}$`))
      await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
      expect(await serious(page), path).toEqual([])
    }
  })

  test('F08-RF-09 em celular o menu vira gaveta', async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    const account = await createAccount(request, { verified: true, name: 'Pessoa Celular' })
    await page.goto('/login')
    await page.getByLabel('Email').fill(account.email)
    await page.getByLabel('Password').fill(account.password)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()

    const nav = page.getByRole('navigation', { name: 'Main' })
    await expect(nav).toBeHidden()
    await page.getByRole('button', { name: 'Open menu' }).click()
    await nav.getByRole('link', { name: 'Jira projects' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Jira projects' })).toBeVisible()
    await expect(nav).toBeHidden()
    expect(await serious(page)).toEqual([])
    // Sem rolagem horizontal na largura de celular (a expressão roda no navegador).
    const overflow = await page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    expect(overflow).toBe(false)
  })
})
