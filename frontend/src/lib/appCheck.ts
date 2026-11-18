/**
 * Token do Firebase App Check (F11-RT-07), mandado em `X-Firebase-AppCheck` em toda chamada à
 * API. Sem `VITE_APPCHECK_SITE_KEY` (local, testes) não há token e o backend roda em `off`.
 */
type Getter = () => Promise<string | null>

let getter: Getter | null = null

export function setAppCheckTokenGetter(fn: Getter | null): void {
  getter = fn
}

/** Nunca falha: sem token, a API decide (em `monitor` só registra). */
export async function appCheckToken(): Promise<string | null> {
  if (!getter) return null
  try {
    return await getter()
  } catch {
    return null
  }
}

export async function withAppCheck(headers: Headers): Promise<Headers> {
  const token = await appCheckToken()
  if (token) headers.set('X-Firebase-AppCheck', token)
  return headers
}
