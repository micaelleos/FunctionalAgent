import { type APIRequestContext, expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F20-02..05 com o modelo real no espaço do sandbox, depois das páginas de teste
// (`scripts/confluence_fixture.py`). ESCREVE no Confluence: rode só com aprovação do PO.
// E2E_REAL_LLM=1 e E2E_CONFLUENCE_WRITE=1 ligam estes testes; a API local precisa de
// CONFLUENCE_WRITE_ENABLED=true. AT-F20-01 pede um projeto do Jira sem espaço
// (E2E_SPACE_PROJECT) e AT-F20-03 cria um épico no Jira (E2E_JIRA_WRITE=1).
const SITE = process.env.JIRA_SANDBOX_URL ?? ''
const EMAIL = process.env.JIRA_SANDBOX_EMAIL ?? ''
const TOKEN = process.env.JIRA_SANDBOX_API_TOKEN ?? ''
const PROJECT = process.env.JIRA_SANDBOX_PROJECT_KEY ?? ''
const SPACE_PROJECT = process.env.E2E_SPACE_PROJECT ?? ''

test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')
test.skip(process.env.E2E_REAL_LLM !== '1', 'precisa do modelo real: E2E_REAL_LLM=1')
test.skip(process.env.E2E_CONFLUENCE_WRITE !== '1', 'escreve no Confluence: E2E_CONFLUENCE_WRITE=1')
test.skip(!SITE || !EMAIL || !TOKEN || !PROJECT, 'precisa de JIRA_SANDBOX_*')
test.setTimeout(300_000)

const auth = `Basic ${Buffer.from(`${EMAIL}:${TOKEN}`).toString('base64')}`

async function wiki(
  request: APIRequestContext,
  path: string,
  init: { method?: string; data?: unknown } = {},
) {
  const response = await request.fetch(`${SITE}/wiki${path}`, {
    method: init.method ?? 'GET',
    headers: { Authorization: auth, Accept: 'application/json' },
    data: init.data,
    maxRedirects: 0,
  })
  expect(response.ok()).toBe(true)
  return response.json()
}

async function pageByTitle(request: APIRequestContext, title: string) {
  const cql = `space = "${PROJECT}" AND type = page AND title = "${title}"`
  const found = await wiki(request, `/rest/api/search?cql=${encodeURIComponent(cql)}&limit=1`)
  const id = found.results[0].content.id as string
  return wiki(request, `/api/v2/pages/${id}?body-format=storage`)
}

async function chat(page: Page, request: APIRequestContext, project: string, link: boolean) {
  const account = await createAccount(request, { verified: true, name: 'Pessoa Docs Escrita' })
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Chat' })).toBeVisible()
  await page.goto('/settings')
  await page.getByLabel('Site URL').fill(SITE)
  await page.getByLabel('Atlassian account email').fill(EMAIL)
  await page.getByLabel('API token', { exact: true }).fill(TOKEN)
  await page.getByRole('button', { name: 'Validate and save' }).click()
  await expect(page.getByText(/Jira connected ·/)).toBeVisible({ timeout: 30_000 })
  await page.goto('/projects')
  const card = page
    .getByRole('listitem')
    .filter({ has: page.getByText(new RegExp(`^${project} · `)) })
  await card.getByRole('button', { name: 'Project docs' }).click()
  if (link) {
    await card.getByRole('button', { name: 'Link', exact: true }).click()
    await expect(
      card.getByText('The agent reads this space before proposing issues:'),
    ).toBeVisible()
    await card.getByRole('link', { name: 'Chat about this project' }).click()
  }
  return card
}

async function send(page: Page, text: string) {
  await page.getByLabel('Message').fill(text)
  await page.getByLabel('Message').press('Enter')
}

const docCard = (page: Page, title: string) =>
  page.getByRole('region', { name: new RegExp(`^(Create|Update) page “${title}”$`) }).last()

test('F20-RF-02 F20-RF-07 AT-F20-02 Constituição escrita a partir da conversa', async ({
  page,
  request,
}) => {
  await chat(page, request, PROJECT, true)
  const registry = await pageByTitle(request, 'Registro de mudanças')
  await send(
    page,
    'Vamos escrever a constituição: dados de clientes nunca saem do Brasil. Versão 1.0.0. ' +
      'Proponha a página sem perguntas.',
  )
  const card = docCard(page, 'Constituição')
  await expect(card).toBeVisible({ timeout: 240_000 })
  await card.getByRole('button', { name: 'Confirm and write' }).click()
  await expect(card.getByRole('status')).toContainText('Written to Confluence', { timeout: 60_000 })

  const constitution = await pageByTitle(request, 'Constituição')
  expect(constitution.body.storage.value).toMatch(/Brasil/)
  expect(constitution.body.storage.value).toMatch(/1\.0\.0/)
  const after = await pageByTitle(request, 'Registro de mudanças')
  expect(after.version.number).toBe(registry.version.number + 1)
  expect(after.body.storage.value).toContain('confirmado por Pessoa Docs Escrita')
})

test('F20-RF-04 AT-F20-04 não sobrescreve edição de outra pessoa', async ({ page, request }) => {
  await chat(page, request, PROJECT, true)
  await send(
    page,
    'Adicione ao glossário o termo Cupom: código que dá desconto no pedido. Proponha sem perguntas.',
  )
  const card = docCard(page, 'Glossário')
  await expect(card).toBeVisible({ timeout: 240_000 })

  // Alguém edita o Glossário no Confluence depois da proposta.
  const glossary = await pageByTitle(request, 'Glossário')
  const edited = `${glossary.body.storage.value}<p>Edição da outra pessoa</p>`
  await wiki(request, `/api/v2/pages/${glossary.id}`, {
    method: 'PUT',
    data: {
      id: glossary.id,
      status: 'current',
      title: glossary.title,
      body: { representation: 'storage', value: edited },
      version: { number: glossary.version.number + 1, message: 'AT-F20-04' },
    },
  })

  await card.getByRole('button', { name: 'Confirm and write' }).click()
  await expect(card.getByRole('status')).toContainText(
    'This page changed since the proposal. Ask the agent to review it again.',
    { timeout: 60_000 },
  )
  const now = await pageByTitle(request, 'Glossário')
  expect(now.body.storage.value).toContain('Edição da outra pessoa')
  expect(now.body.storage.value).not.toContain('Cupom')
})

test('F20-RT-01 AT-F20-05 nada é escrito sem Confirm', async ({ page, request }) => {
  await chat(page, request, PROJECT, true)
  const before = await pageByTitle(request, 'Regras de negócio')
  await send(
    page,
    'Nova regra: pedido cancelado depois do faturamento gera estorno em até 7 dias. Proponha a ' +
      'atualização da página de regras sem perguntas.',
  )
  const card = docCard(page, 'Regras de negócio')
  await expect(card).toBeVisible({ timeout: 240_000 })
  await card.getByRole('button', { name: 'Discard' }).click()
  await expect(card.getByRole('status')).toContainText('Nothing was written to Confluence')
  const after = await pageByTitle(request, 'Regras de negócio')
  expect(after.version.number).toBe(before.version.number)
})

test('F20-RF-01 AT-F20-01 criar o espaço com o modelo', async ({ page, request }) => {
  test.skip(!SPACE_PROJECT, 'precisa de um projeto do Jira sem espaço: E2E_SPACE_PROJECT')
  const card = await chat(page, request, SPACE_PROJECT, false)
  await card.getByRole('link', { name: 'Create space' }).click()
  await page.getByLabel('Message').press('Enter')
  const proposal = page.getByRole('region', { name: /^Create space “/ }).last()
  await expect(proposal).toBeVisible({ timeout: 240_000 })
  await proposal.getByRole('button', { name: 'Confirm and create space' }).click()
  await expect(proposal.getByRole('status')).toContainText('Written to Confluence', {
    timeout: 120_000,
  })
  const cql = `space = "${SPACE_PROJECT}" AND type = page AND label = "specflow"`
  const pages = await wiki(request, `/rest/api/search?cql=${encodeURIComponent(cql)}&limit=25`)
  const titles = (pages.results as { content: { title: string } }[]).map((r) => r.content.title)
  for (const title of [
    'Início',
    'Constituição',
    'Glossário',
    'Regras de negócio',
    'Arquitetura',
    'Decisões (ADR)',
    'Roadmap',
    'Features',
    'Registro de mudanças',
  ])
    expect(titles).toContain(title)
  await page.goto('/projects')
  const linked = page
    .getByRole('listitem')
    .filter({ has: page.getByText(new RegExp(`^${SPACE_PROJECT} · `)) })
  await linked.getByRole('button', { name: 'Project docs' }).click()
  await expect(
    linked.getByText('The agent reads this space before proposing issues:'),
  ).toBeVisible()
})

test('F20-RF-05 F20-RF-03 AT-F20-03 Roadmap acompanha o épico criado', async ({
  page,
  request,
}) => {
  test.skip(process.env.E2E_JIRA_WRITE !== '1', 'cria um épico no Jira: E2E_JIRA_WRITE=1')
  await chat(page, request, PROJECT, true)
  await send(
    page,
    'Épico "Cupons de desconto" com duas histórias: aplicar cupom no carrinho e recusar cupom ' +
      'expirado. Fora de escopo: cupom por e-mail. Testes de unidade e E2E. Proponha sem perguntas.',
  )
  const epic = page.getByRole('region', { name: /^Create Epic in / }).last()
  await expect(epic).toBeVisible({ timeout: 240_000 })
  await epic.getByRole('button', { name: 'Confirm and create' }).click()
  const status = epic.getByRole('status')
  await expect(status).toContainText('Created as', { timeout: 60_000 })
  const key = ((await status.textContent()) ?? '').match(/[A-Z]+-\d+/)?.[0] ?? ''
  await send(page, 'Confirmei. Alinhe a documentação do projeto, sem perguntas.')
  const roadmap = docCard(page, 'Roadmap')
  await expect(roadmap).toBeVisible({ timeout: 240_000 })
  await expect(roadmap.getByRole('region', { name: /./ }).first()).toBeVisible()
  await roadmap.getByRole('button', { name: 'Confirm and write' }).click()
  await expect(roadmap.getByRole('status')).toContainText('Written to Confluence', {
    timeout: 60_000,
  })
  const page_ = await pageByTitle(request, 'Roadmap')
  expect(page_.body.storage.value).toContain(key)
})
