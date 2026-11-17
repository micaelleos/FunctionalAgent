import type { components } from './api-schema'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface Health {
  status: 'ok'
  version: string
  env: string
}

export type Profile = components['schemas']['Profile']

export async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch(`${API_BASE_URL}/health`, { signal })
  if (!response.ok) {
    throw new Error(`API respondeu ${response.status}`)
  }
  return (await response.json()) as Health
}

/** Erro da API no formato Problem Details (F03-RT-05). `code` escolhe a mensagem na interface. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    /** Corpo inteiro do problema (ex.: `action` nos erros da confirmação, F06). */
    readonly body: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const problem = (await response.json()) as {
      code?: string
      title?: string
      detail?: string
    } & Record<string, unknown>
    return new ApiError(
      response.status,
      problem.code ?? `http-${response.status}`,
      problem.detail ?? problem.title ?? `API respondeu ${response.status}`,
      problem,
    )
  } catch {
    return new ApiError(
      response.status,
      `http-${response.status}`,
      `API respondeu ${response.status}`,
    )
  }
}

export type TokenGetter = (forceRefresh: boolean) => Promise<string | null>

/**
 * Chama a API com o ID token. Em 401, renova o token e tenta mais uma vez (F03-RT-03): cobre o
 * token que expirou entre a leitura e o uso.
 */
export async function apiFetch(
  path: string,
  getToken: TokenGetter,
  init: RequestInit = {},
): Promise<Response> {
  const send = async (forceRefresh: boolean) => {
    const headers = new Headers(init.headers)
    const token = await getToken(forceRefresh)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    return fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  }
  let response = await send(false)
  if (response.status === 401) response = await send(true)
  if (!response.ok) throw await toApiError(response)
  return response
}

export function createAccountApi(getToken: TokenGetter) {
  return {
    getMe: async (): Promise<Profile> =>
      (await (await apiFetch('/api/v1/me', getToken)).json()) as Profile,
    exportMe: async (): Promise<Blob> => (await apiFetch('/api/v1/me/export', getToken)).blob(),
    deleteMe: async (): Promise<void> => {
      await apiFetch('/api/v1/me', getToken, { method: 'DELETE' })
    },
  }
}

export type AccountApi = ReturnType<typeof createAccountApi>
