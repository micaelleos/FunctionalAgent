// F08-RT-06: mede fps e long tasks enquanto o chat recebe 5000 tokens (scripts/perf/README.md).
import { createRequire } from 'node:module'
const require = createRequire('/workspaces/FunctionalAgent/frontend/package.json')
const { chromium } = require('@playwright/test')
const toolkit = 'http://localhost:9099/identitytoolkit.googleapis.com/v1'
const email = `perf-${Date.now()}@teste.dev`,
  password = 's-perf-1'
const post = (u, b, h = {}) =>
  fetch(u, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...h },
    body: JSON.stringify(b),
  }).then((r) => r.json())
const { localId } = await post(`${toolkit}/accounts:signUp?key=demo-key`, {
  email,
  password,
  returnSecureToken: true,
})
await post(
  `${toolkit}/projects/demo-functional-agent/accounts:update`,
  { localId, displayName: 'Pessoa Perf', emailVerified: true },
  { Authorization: 'Bearer owner' },
)
const browser = await chromium.launch()
const page = await browser.newPage()
await page.goto('http://localhost:5174/login')
await page.getByLabel('Email').fill(email)
await page.getByLabel('Password').fill(password)
await page.getByRole('button', { name: 'Sign in', exact: true }).click()
await page.getByRole('heading', { level: 1, name: 'Chat' }).waitFor()
await page.evaluate(() => {
  const w = window
  w.__frames = []
  w.__long = []
  new PerformanceObserver((l) => l.getEntries().forEach((e) => w.__long.push(e.duration))).observe({
    type: 'longtask',
    buffered: false,
  })
  const tick = (t) => {
    w.__frames.push(t)
    requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
})
await page.getByLabel('Message').fill('Gere 5 mil tokens')
const t0 = Date.now()
await page.getByLabel('Message').press('Enter')
await page.getByRole('button', { name: 'Stop' }).waitFor()
await page.getByRole('button', { name: 'Send' }).waitFor({ timeout: 120000 })
const ms = Date.now() - t0
const r = await page.evaluate(() => {
  const f = window.__frames,
    gaps = f
      .slice(1)
      .map((t, i) => t - f[i])
      .sort((a, b) => a - b)
  return {
    frames: f.length,
    seconds: (f.at(-1) - f[0]) / 1000,
    fps: f.length / ((f.at(-1) - f[0]) / 1000),
    p95FrameMs: gaps[Math.floor(gaps.length * 0.95)],
    maxFrameMs: gaps.at(-1),
    longTasks: window.__long.length,
    maxLongTaskMs: Math.max(0, ...window.__long),
  }
})
console.log(JSON.stringify({ tokens: 5000, streamMs: ms, ...r, fps: +r.fps.toFixed(1) }))
await browser.close()
