// Teste de carga da API (F11-RT-08): 50 usuários simultâneos conversando com o LLM fake.
// Cada usuário manda perto do ritmo máximo que o rate limit permite (10/min): pausa de 6 a 9 s, com
// início espalhado nos primeiros 6 s para os 50 não andarem em fase (ondas de 50 a cada 6 s, que
// usuários reais não fazem). `PAUSE=1 JITTER=0` (com RATE_LIMIT_PER_MINUTE alto) vira saturação.
// Contra `make dev` com a cota alta (o rate limit padrão continua valendo):
//   DAILY_MESSAGE_QUOTA=100000 docker compose up -d emulators backend
//   docker run --rm -i --network host grafana/k6:0.57.0 run - < scripts/load/chat.js
// Metas: erro < 1% e p95 < 500 ms. Com o LLM de eco, a duração da requisição é o overhead do
// backend (Auth, Firestore, cota, histórico, gravação).
import http from 'k6/http'
import { check, sleep } from 'k6'

const API = __ENV.API_URL || 'http://localhost:8000'
const AUTH = __ENV.AUTH_URL || 'http://localhost:9099'
const PROJECT = 'demo-functional-agent'
const USERS = 50
const PAUSE = Number(__ENV.PAUSE || 6)
const JITTER = Number(__ENV.JITTER ?? 3)
const toolkit = `${AUTH}/identitytoolkit.googleapis.com/v1`

export const options = {
  scenarios: {
    chat: { executor: 'constant-vus', vus: USERS, duration: __ENV.DURATION || '2m' },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{name:chat}': ['p(95)<500'],
  },
}

function account(i) {
  const email = `carga-${i}-${Date.now()}@teste.dev`
  const password = `senha-${i}-carga`
  const json = { headers: { 'Content-Type': 'application/json' } }
  const signUp = http.post(
    `${toolkit}/accounts:signUp?key=demo-key`,
    JSON.stringify({ email, password, returnSecureToken: true }),
    json,
  ).json()
  http.post(
    `${toolkit}/projects/${PROJECT}/accounts:update`,
    JSON.stringify({ localId: signUp.localId, emailVerified: true }),
    { headers: { 'Content-Type': 'application/json', Authorization: 'Bearer owner' } },
  )
  // Token novo, já com email_verified = true.
  const signIn = http.post(
    `${toolkit}/accounts:signInWithPassword?key=demo-key`,
    JSON.stringify({ email, password, returnSecureToken: true }),
    json,
  ).json()
  return signIn.idToken
}

export function setup() {
  const tokens = []
  for (let i = 0; i < USERS; i++) tokens.push(account(i))
  return { tokens }
}

export default function (data) {
  if (__ITER === 0 && JITTER > 0) sleep(Math.random() * PAUSE)
  const token = data.tokens[(__VU - 1) % data.tokens.length]
  const response = http.post(
    `${API}/api/v1/conversations/new/messages`,
    JSON.stringify({ content: `Mensagem de carga ${__ITER}` }),
    {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      tags: { name: 'chat' },
      timeout: '30s',
    },
  )
  check(response, {
    '200 (nunca 429 no ritmo do rate limit)': (r) => r.status === 200,
    'turno completo': (r) => typeof r.body === 'string' && r.body.includes('event: done'),
  })
  sleep(PAUSE + Math.random() * JITTER)
}
