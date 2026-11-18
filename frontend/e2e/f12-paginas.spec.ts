import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

// AT-F12-03: rodapé da página inicial com ajuda e status da API; Privacy pública, sem login e sem
// violações sérias de acessibilidade. Roda contra `make dev` ou prd (E2E_BASE_URL); não escreve nada.
async function serious(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.help}`)
}

test('F12-RF-03 F12-RF-04 AT-F12-03 ajuda e privacidade públicas e acessíveis', async ({
  page,
}) => {
  await page.goto('/about') // endereço antigo
  await expect(page).toHaveURL(/\/$/)
  const footer = page.getByRole('contentinfo')
  await expect(footer.getByRole('link', { name: /Help/ })).toHaveAttribute(
    'href',
    /github\.com\/micaelleos\/FunctionalAgent\/issues$/,
  )
  await expect(footer.getByText('API: ok')).toBeVisible({ timeout: 20_000 })

  await footer.getByRole('link', { name: 'Privacy' }).click()
  await expect(page).toHaveURL(/\/privacy$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Privacy' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 2, name: 'Your choices' })).toBeVisible()
  expect(await serious(page)).toEqual([])
})
