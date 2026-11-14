import type { APIRequestContext } from '@playwright/test'

// Acesso aos emuladores do Firebase nos E2E da F03 (só com E2E_EMULATORS=1, via `make dev`).
export const EMULATORS = process.env.E2E_EMULATORS === '1'
export const PROJECT = 'demo-functional-agent'
export const AUTH = process.env.E2E_AUTH_EMULATOR ?? 'http://localhost:9099'
export const FIRESTORE = process.env.E2E_FIRESTORE_EMULATOR ?? 'http://localhost:8081'
export const API = process.env.E2E_API_URL ?? 'http://localhost:8000'

const toolkit = `${AUTH}/identitytoolkit.googleapis.com/v1`
const owner = { Authorization: 'Bearer owner' }

export const randomEmail = () => `e2e-${Math.random().toString(36).slice(2, 10)}@teste.dev`

/** Confirma o e-mail pelo link que o emulador "enviou". */
export async function confirmEmail(request: APIRequestContext, email: string): Promise<void> {
  const response = await request.get(`${AUTH}/emulator/v1/projects/${PROJECT}/oobCodes`)
  const { oobCodes } = (await response.json()) as {
    oobCodes: { email: string; requestType: string; oobLink: string }[]
  }
  const code = oobCodes.reverse().find((c) => c.email === email && c.requestType === 'VERIFY_EMAIL')
  if (!code) throw new Error(`sem e-mail de verificação para ${email}`)
  await request.get(code.oobLink)
}

/** Cria uma conta direto no emulador e devolve um ID token. */
export async function createAccount(
  request: APIRequestContext,
  { verified, name = 'Pessoa Teste' }: { verified: boolean; name?: string },
): Promise<{ email: string; password: string; uid: string; token: string }> {
  const email = randomEmail()
  const password = `s-${Math.random().toString(36).slice(2)}`
  const signUp = await request.post(`${toolkit}/accounts:signUp?key=demo-key`, {
    data: { email, password, returnSecureToken: true },
  })
  const { localId } = (await signUp.json()) as { localId: string }
  await request.post(`${toolkit}/projects/${PROJECT}/accounts:update`, {
    headers: owner,
    data: { localId, displayName: name, emailVerified: verified },
  })
  const signIn = await request.post(`${toolkit}/accounts:signInWithPassword?key=demo-key`, {
    data: { email, password, returnSecureToken: true },
  })
  const { idToken } = (await signIn.json()) as { idToken: string }
  return { email, password, uid: localId, token: idToken }
}

/** Status HTTP do documento users/{uid} no banco specflow (200 existe, 404 não). */
export async function userDocStatus(request: APIRequestContext, uid: string): Promise<number> {
  const url = `${FIRESTORE}/v1/projects/${PROJECT}/databases/specflow/documents/users/${uid}`
  return (await request.get(url, { headers: owner })).status()
}
