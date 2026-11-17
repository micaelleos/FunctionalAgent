// Lighthouse (mobile) em /chat logado, no build de produção local (F08-RT-03).
import { createRequire } from 'node:module'
import { writeFileSync } from 'node:fs'
import lighthouse from 'lighthouse'
const require = createRequire('/workspaces/FunctionalAgent/frontend/package.json')
const { chromium } = require('@playwright/test')

const BASE = 'http://localhost:5173'
const toolkit = 'http://localhost:9099/identitytoolkit.googleapis.com/v1'
const email = `lh-${Date.now()}@teste.dev`,
  password = 's-lighthouse-1'
const post = (url, body, headers = {}) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  }).then((r) => r.json())
const { localId } = await post(`${toolkit}/accounts:signUp?key=demo-key`, {
  email,
  password,
  returnSecureToken: true,
})
await post(
  `${toolkit}/projects/demo-functional-agent/accounts:update`,
  { localId, displayName: 'Pessoa LH', emailVerified: true },
  { Authorization: 'Bearer owner' },
)

const port = 9333
const browser = await chromium.launchPersistentContext(process.argv[2], {
  args: [`--remote-debugging-port=${port}`],
})
const page = browser.pages()[0] ?? (await browser.newPage())
await page.goto(`${BASE}/login`)
await page.getByLabel('Email').fill(email)
await page.getByLabel('Password').fill(password)
await page.getByRole('button', { name: 'Sign in', exact: true }).click()
await page.getByRole('heading', { level: 1, name: 'Chat' }).waitFor()
// Um histórico com Markdown, tabela e código, como uma conversa real.
const box = page.getByLabel('Message')
await box.fill(
  '## Épico\n\nResumo com **negrito**.\n\n| CA | Tipo |\n|---|---|\n| CA-01 | principal |\n\n```gherkin\nCenário: pagar\n```',
)
await box.press('Enter')
await page.waitForURL(/\/chat\/[\w-]+$/)
await page.locator('.chat-markdown table').last().waitFor()
const url = page.url()

const result = await lighthouse(url, {
  port,
  output: ['json', 'html'],
  logLevel: 'error',
  disableStorageReset: true,
  onlyCategories: ['performance', 'accessibility', 'best-practices'],
})
writeFileSync(process.argv[3] + '.json', result.report[0])
writeFileSync(process.argv[3] + '.html', result.report[1])
const c = result.lhr.categories
console.log(
  JSON.stringify({
    url: url.replace(/[\w-]+$/, '{id}'),
    performance: Math.round(c.performance.score * 100),
    accessibility: Math.round(c.accessibility.score * 100),
    bestPractices: Math.round(c['best-practices'].score * 100),
    lcp: result.lhr.audits['largest-contentful-paint'].displayValue,
    tbt: result.lhr.audits['total-blocking-time'].displayValue,
    cls: result.lhr.audits['cumulative-layout-shift'].displayValue,
    formFactor: result.lhr.configSettings.formFactor,
  }),
)
await browser.close()
