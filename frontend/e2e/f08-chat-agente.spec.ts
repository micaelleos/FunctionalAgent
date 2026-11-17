import { expect, type Page, test } from '@playwright/test'

import { createAccount, EMULATORS } from './emulators'

// AT-F08-02 e AT-F08-04 com o modelo real (API local com LLM_PROVIDER=google_vertexai) e o Jira
// sandbox só para leitura: o cartão aparece, mas nada é confirmado, então nada é escrito no Jira.
// E2E_REAL_LLM=1 liga estes testes; credenciais do sandbox vêm do ambiente (.env.local).
const SITE = process.env.JIRA_SANDBOX_URL ?? ''
const EMAIL = process.env.JIRA_SANDBOX_EMAIL ?? ''
const TOKEN = process.env.JIRA_SANDBOX_API_TOKEN ?? ''
const PROJECT = process.env.JIRA_SANDBOX_PROJECT_KEY ?? ''

test.skip(!EMULATORS, 'precisa dos emuladores: E2E_EMULATORS=1 com `make dev`')
test.skip(process.env.E2E_REAL_LLM !== '1', 'precisa do modelo real: E2E_REAL_LLM=1')
test.skip(!SITE || !EMAIL || !TOKEN || !PROJECT, 'precisa de JIRA_SANDBOX_*')
test.setTimeout(180_000)

async function signInWithJira(page: Page, request: Parameters<typeof createAccount>[0]) {
  const account = await createAccount(request, { verified: true, name: 'Pessoa Agente' })
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
  await page.goto('/chat')
}

async function send(page: Page, text: string) {
  await page.getByLabel('Message').fill(text)
  await page.getByLabel('Message').press('Enter')
}

test.describe('F08 chat com o agente real', () => {
  test('F08-RF-03 F08-RF-04 AT-F08-02 indicador de ferramenta e cartão sem confirmar', async ({
    page,
    request,
  }) => {
    await signInWithJira(page, request)
    await page.goto(`/chat?projeto=${PROJECT}`)
    await expect(page.getByText(`Pinned project: ${PROJECT}`)).toBeVisible()

    await send(
      page,
      'Crie uma task: adicionar um botão "Copiar link" na página de detalhes do pedido, que copia ' +
        'a URL do pedido para a área de transferência e mostra "Link copiado" por 2 segundos. ' +
        'Critérios: o botão aparece em pedidos de qualquer status; sem permissão de clipboard, ' +
        'mostra o link selecionado para cópia manual. Fora do escopo: compartilhar por e-mail. ' +
        'Já está completo, pode propor sem perguntar mais nada.',
    )

    // Indicador de ferramenta (role=status) enquanto o agente usa as ferramentas.
    await expect(page.getByRole('status').filter({ hasText: /…$/ }).first()).toBeVisible({
      timeout: 60_000,
    })
    const card = page.getByRole('region', { name: new RegExp(`in ${PROJECT}$`) }).first()
    await expect(card).toBeVisible({ timeout: 120_000 })
    await expect(card.getByRole('button', { name: 'Confirm and create' })).toBeVisible()
    await expect(card.getByRole('button', { name: 'Reject' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send' })).toBeVisible({ timeout: 120_000 })

    // O cartão continua lá depois de recarregar, ainda pendente. Nada é confirmado.
    await page.reload()
    const again = page.getByRole('region', { name: new RegExp(`in ${PROJECT}$`) }).first()
    await expect(again.getByRole('button', { name: 'Confirm and create' })).toBeVisible()
  })

  test('F08-RF-06 F08-RT-09 AT-F08-04 parar grava a parte já enviada como interrompida', async ({
    page,
    request,
  }) => {
    await signInWithJira(page, request)

    await send(
      page,
      'Sem usar ferramentas e sem perguntas, escreva um texto longo (umas 800 palavras) explicando ' +
        'o que é BDD, com vários exemplos de cenários Gherkin para um checkout de e-commerce.',
    )
    const reply = page.locator('.chat-markdown').last()
    await expect(reply).toContainText(/\w{3,}/, { timeout: 60_000 })
    await page.getByRole('button', { name: 'Stop' }).click()

    await expect(page.getByText('Interrupted: you stopped this answer.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
    await expect(page).toHaveURL(/\/chat\/[\w-]+$/)

    await page.waitForTimeout(3000) // o servidor grava a parte parcial ao perceber a desconexão
    await page.reload()
    await expect(page.getByText('Interrupted: you stopped this answer.')).toBeVisible()
    await expect(page.locator('.chat-markdown').last()).toContainText(/\w{3,}/)
  })
})
