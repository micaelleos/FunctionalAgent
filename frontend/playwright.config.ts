import { defineConfig, devices } from '@playwright/test'

// Testes de aceitação contra um ambiente publicado (dev, preview ou prd).
// E2E_BASE_URL é a URL do Hosting; sem ela, usa o Vite local (npm run dev).
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: { baseURL, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
