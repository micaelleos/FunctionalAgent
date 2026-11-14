import { expect, test } from '@playwright/test'

// AT-F02-01 (F02-RF-01, F02-RF-03) e F02-RT-06. Rodam no deploy.yml contra o Hosting recém-publicado.
// E2E_EXPECTED_VERSION é o SHA publicado; sem ela, só confere que há uma versão.
const expectedVersion = process.env.E2E_EXPECTED_VERSION

test.describe('F02 infraestrutura e deploy', () => {
  test('AT-F02-01 F02-RF-01 F02-RF-03 frontend publicado exibe o status e a versão do backend', async ({
    page,
  }) => {
    await page.goto('/')

    const status = page.getByText('API: ok')
    await expect(status).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/\(versão \S+, ambiente \S+\)/)).toBeVisible()
    if (expectedVersion) {
      await expect(page.getByText(`(versão ${expectedVersion},`, { exact: false })).toBeVisible()
    }
  })

  test('F02-RT-06 Hosting envia os cabeçalhos de segurança', async ({ request, baseURL }) => {
    test.skip(!baseURL?.startsWith('https://'), 'cabeçalhos só existem no Firebase Hosting')

    const response = await request.get('/')
    const headers = response.headers()

    expect(headers['content-security-policy']).toContain("default-src 'self'")
    expect(headers['content-security-policy']).toContain("frame-ancestors 'none'")
    expect(headers['strict-transport-security']).toContain('max-age=31536000')
    expect(headers['x-content-type-options']).toBe('nosniff')
    expect(headers['referrer-policy']).toBe('strict-origin-when-cross-origin')
  })
})
