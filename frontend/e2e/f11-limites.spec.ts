import { expect, test } from '@playwright/test'

import { API, createAccount, EMULATORS } from './emulators'

// AT-F11-01/02 contra `make dev` com o LLM de eco. A cota precisa ser configurada no backend:
//   AT-F11-01: DAILY_MESSAGE_QUOTA=3 docker compose up -d backend  → E2E_QUOTA=3
//   AT-F11-02: cota padrão (20) e RATE_LIMIT_PER_MINUTE padrão (10) → sem E2E_QUOTA
// O rate limit é decidido antes da cota; com cota 3, a 4ª mensagem já é recusada pela cota.
test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')
test.skip(process.env.E2E_REAL_LLM === '1', 'usa o modelo de eco')

const QUOTA = Number(process.env.E2E_QUOTA ?? 20)

test.describe('F11 limites de uso', () => {
  test('F11-RF-01 F11-RF-02 AT-F11-01 cota diária: "3 of 3" e a mensagem de limite', async ({
    page,
    request,
  }) => {
    test.skip(QUOTA !== 3, 'precisa do backend com DAILY_MESSAGE_QUOTA=3 (E2E_QUOTA=3)')
    const account = await createAccount(request, { verified: true, name: 'Pessoa Cota' })
    await page.goto('/login')
    await page.getByLabel('Email').fill(account.email)
    await page.getByLabel('Password').fill(account.password)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
    await expect(page.getByText('0 of 3')).toBeVisible()

    const box = page.getByLabel('Message')
    for (let i = 1; i <= 3; i++) {
      await box.fill(`Mensagem ${i}`)
      await box.press('Enter')
      await expect(page.getByText(`Você disse: Mensagem ${i}`)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
    }
    await expect(page.getByText('3 of 3')).toBeVisible()

    await box.fill('Mensagem 4')
    await box.press('Enter')
    const alert = page.getByRole('alert')
    await expect(alert).toHaveText(
      /You've reached today's limit\. It renews at 00:00 \(Brasília time\)\./,
    )
    await expect(alert.getByRole('button', { name: 'Try again' })).toHaveCount(0)
    await expect(box).toHaveValue('Mensagem 4') // o texto volta ao campo
    await expect(page.getByText('3 of 3')).toBeVisible()
  })

  test('F11-RF-03 AT-F11-02 rate limit: 429 "rate-limited" com Retry-After a partir da 11ª', async ({
    request,
  }) => {
    test.skip(QUOTA < 15, 'precisa da cota padrão (sem E2E_QUOTA)')
    const { token } = await createAccount(request, { verified: true })
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

    const started = Date.now()
    const statuses: number[] = []
    let refused: { status: number; retryAfter: string | null; body: unknown } | null = null
    for (let i = 1; i <= 15; i++) {
      const response = await request.post(`${API}/api/v1/conversations/new/messages`, {
        headers,
        data: { content: `Rajada ${i}` },
      })
      statuses.push(response.status())
      if (response.status() === 429 && !refused) {
        refused = {
          status: 429,
          retryAfter: response.headers()['retry-after'] ?? null,
          body: await response.json(),
        }
      }
    }
    expect(Date.now() - started).toBeLessThan(10_000)
    expect(statuses.slice(0, 10)).toEqual(Array(10).fill(200))
    expect(statuses.slice(10)).toEqual(Array(5).fill(429))
    expect(refused?.body).toMatchObject({ code: 'rate-limited', status: 429 })
    expect(Number(refused?.retryAfter)).toBeGreaterThan(0)
  })
})
