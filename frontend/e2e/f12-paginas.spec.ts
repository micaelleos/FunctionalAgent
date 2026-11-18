import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

// AT-F12-03: About e Privacy públicas, sem login, sem violações sérias de acessibilidade. Roda contra
// `make dev` ou contra prd (E2E_BASE_URL); não escreve nada.
async function serious(page: import('@playwright/test').Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.help}`)
}

test('F12-RF-03 F12-RF-04 AT-F12-03 About e Privacy são públicas e acessíveis', async ({
  page,
}) => {
  await page.goto('/about')
  const how = page.getByRole('region', { name: 'How it works' })
  for (const step of [
    'Create an account',
    'Connect Jira',
    'Chat',
    'Confirm before anything is written',
  ]) {
    await expect(how.getByRole('heading', { name: step, exact: true })).toBeVisible()
  }
  await expect(page.getByRole('link', { name: 'Open an issue on GitHub' })).toHaveAttribute(
    'href',
    /github\.com\/micaelleos\/FunctionalAgent\/issues$/,
  )
  expect(await serious(page)).toEqual([])

  await page.getByRole('link', { name: 'Privacy' }).click()
  await expect(page).toHaveURL(/\/privacy$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Privacy' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 2, name: 'Your choices' })).toBeVisible()
  expect(await serious(page)).toEqual([])
})
