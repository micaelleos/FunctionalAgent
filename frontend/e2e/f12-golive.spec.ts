import { expect, type APIRequestContext, type Page, test } from '@playwright/test'

// AT-F12-01: jornada completa em PRODUÇÃO (E2E_BASE_URL=https://specsflow-ai.web.app), com o Gemini
// real e o Jira sandbox do PO. ESCREVE NO JIRA (1 épico + 1 story no projeto do sandbox, mantidos como
// evidência). Só roda com E2E_PRD=1, que o PO autoriza. Tudo vem do `.env.local`, nunca do repo:
//   E2E_PRD_EMAIL / E2E_PRD_PASSWORD   conta de teste em prd, já com o e-mail confirmado
//   E2E_APPCHECK_DEBUG_TOKEN           debug token do App Check registrado no console do Firebase
//   JIRA_SANDBOX_URL / _EMAIL / _API_TOKEN / _PROJECT_KEY
const env = (name: string) => process.env[name] ?? ''
const SITE = env('JIRA_SANDBOX_URL')
const PROJECT = env('JIRA_SANDBOX_PROJECT_KEY')

test.skip(process.env.E2E_PRD !== '1', 'escreve no Jira em produção: E2E_PRD=1')
test.skip(
  [
    'E2E_PRD_EMAIL',
    'E2E_PRD_PASSWORD',
    'E2E_APPCHECK_DEBUG_TOKEN',
    'JIRA_SANDBOX_URL',
    'JIRA_SANDBOX_EMAIL',
    'JIRA_SANDBOX_API_TOKEN',
    'JIRA_SANDBOX_PROJECT_KEY',
  ].some((name) => !env(name)),
  'faltam variáveis do .env.local (conta de teste, debug token, JIRA_SANDBOX_*)',
)
test.setTimeout(420_000)

test.beforeEach(async ({ page }) => {
  // Com o debug token, o SDK do App Check troca o token sem reCAPTCHA (navegador automatizado).
  await page.addInitScript((token) => {
    ;(
      globalThis as unknown as { FIREBASE_APPCHECK_DEBUG_TOKEN: string }
    ).FIREBASE_APPCHECK_DEBUG_TOKEN = token
  }, env('E2E_APPCHECK_DEBUG_TOKEN'))
})

async function signIn(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(env('E2E_PRD_EMAIL'))
  await page.getByLabel('Password').fill(env('E2E_PRD_PASSWORD'))
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
}

async function ensureJira(page: Page) {
  await page.goto('/settings')
  const connected = page.getByText(/Jira connected ·/)
  if (await connected.isVisible({ timeout: 10_000 }).catch(() => false)) return
  await page.getByLabel('Site URL').fill(SITE)
  await page.getByLabel('Atlassian account email').fill(env('JIRA_SANDBOX_EMAIL'))
  await page.getByLabel('API token', { exact: true }).fill(env('JIRA_SANDBOX_API_TOKEN'))
  await page.getByRole('button', { name: 'Validate and save' }).click()
  await expect(connected).toBeVisible({ timeout: 30_000 })
}

/** Manda a mensagem, confirma o cartão do tipo pedido e devolve a chave criada. */
async function proposeAndConfirm(page: Page, type: 'Epic' | 'Story', text: string) {
  const box = page.getByLabel('Message')
  await box.fill(text)
  await box.press('Enter')
  const card = page.getByRole('region', { name: `Create ${type} in ${PROJECT}` }).last()
  await card.getByRole('button', { name: 'Confirm and create' }).click({ timeout: 180_000 })
  const created = card.getByText(/^Created as /)
  await expect(created).toBeVisible({ timeout: 60_000 })
  const key = ((await created.textContent()) ?? '').match(new RegExp(`${PROJECT}-\\d+`))?.[0]
  expect(key, `chave do ${type} no cartão`).toBeTruthy()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible({ timeout: 120_000 })
  return key as string
}

/** Lê o issue direto no Jira (a credencial vai só no cabeçalho; nada é impresso). */
async function jiraIssue(request: APIRequestContext, key: string) {
  const auth = Buffer.from(`${env('JIRA_SANDBOX_EMAIL')}:${env('JIRA_SANDBOX_API_TOKEN')}`)
  const response = await request.get(
    `${new URL(SITE).origin}/rest/api/3/issue/${key}?fields=issuetype,parent,summary`,
    { headers: { Authorization: `Basic ${auth.toString('base64')}`, Accept: 'application/json' } },
  )
  expect(response.status(), `GET ${key} no Jira`).toBe(200)
  return (await response.json()) as {
    fields: { issuetype: { name: string }; parent?: { key: string }; summary: string }
  }
}

test('F12-RF-01 F12-RT-02 AT-F12-01 jornada completa em produção', async ({ page, request }) => {
  await signIn(page)
  await ensureJira(page)

  await page.goto(`/chat?projeto=${PROJECT}`)
  const epic = await proposeAndConfirm(
    page,
    'Epic',
    'Crie um épico: "Prazo de entrega na página do produto". Objetivo: o cliente vê, antes de ' +
      'comprar, quando o pedido chega, calculado pelo CEP. Métrica: menos abandono de carrinho por ' +
      'dúvida de prazo. Fora do escopo: frete grátis. Está completo, pode propor sem perguntar.',
  )
  const story = await proposeAndConfirm(
    page,
    'Story',
    `Agora crie uma story filha do épico ${epic}: como cliente, quero informar meu CEP na página ` +
      'do produto e ver "Chega em N dias úteis". Critérios: CEP válido mostra o prazo; CEP ' +
      'inválido mostra "CEP inválido"; sem CEP, nada aparece. Está completo, pode propor.',
  )
  const conversation = new URL(page.url()).pathname

  // Os dois issues existem no Jira, a story dentro do épico.
  expect((await jiraIssue(request, epic)).fields.issuetype.name).toMatch(/epic|épico/i)
  const storyIssue = await jiraIssue(request, story)
  expect(storyIssue.fields.parent?.key).toBe(epic)

  // Aparecem em "Issues".
  await page.goto('/issues')
  for (const key of [epic, story]) {
    await expect(page.getByRole('link', { name: key, exact: true })).toBeVisible({
      timeout: 30_000,
    })
  }

  // A conversa continua lá depois de sair e entrar de novo.
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/(login)?$/)
  await signIn(page)
  await page.goto(conversation)
  await expect(page.getByText(new RegExp(`Created as ${epic}`))).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText(new RegExp(`Created as ${story}`))).toBeVisible()

  test.info().annotations.push({ type: 'issues', description: `${epic}, ${story}` })
})
