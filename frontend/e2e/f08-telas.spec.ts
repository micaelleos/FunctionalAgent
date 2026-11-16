import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// Telas principais (F08-RF-10) contra `make dev`, sem dados de demonstração: o que vai para
// produção. Cada tela abre pelo menu, mostra o estado vazio e passa no axe (F08-RT-04).
test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')

const SCREENS = [
  ['Chat', '/chat', 'Chat'],
  ['Projetos Jira', '/projetos', 'Projetos Jira'],
  ['Issues criadas', '/issues', 'Issues criadas'],
  ['Configurações', '/configuracoes', 'Configurações'],
  ['Minha conta', '/conta', 'Minha conta'],
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
    await expect(page.getByRole('heading', { level: 1, name: /backlog no Jira/ })).toBeVisible()
    expect(await serious(page)).toEqual([])
    await page.getByRole('link', { name: 'Começar agora' }).click()
    await expect(page).toHaveURL(/\/cadastro$/)
  })

  test('F08-RF-10 F08-RT-04 F08-RT-08 menu leva a cada tela, sem dados inventados e sem violações', async ({
    page,
    request,
  }) => {
    const account = await createAccount(request, { verified: true, name: 'Pessoa Telas' })
    await page.goto('/login')
    await page.getByLabel('E-mail').fill(account.email)
    await page.getByLabel('Senha').fill(account.password)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
    await expect(page.getByText('Dados de demonstração')).toHaveCount(0)

    const nav = page.getByRole('navigation', { name: 'Principal' })
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
    await page.getByLabel('E-mail').fill(account.email)
    await page.getByLabel('Senha').fill(account.password)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()

    const nav = page.getByRole('navigation', { name: 'Principal' })
    await expect(nav).toBeHidden()
    await page.getByRole('button', { name: 'Abrir menu' }).click()
    await nav.getByRole('link', { name: 'Projetos Jira' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Projetos Jira' })).toBeVisible()
    await expect(nav).toBeHidden()
    expect(await serious(page)).toEqual([])
    // Sem rolagem horizontal na largura de celular (a expressão roda no navegador).
    const overflow = await page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    expect(overflow).toBe(false)
  })
})
