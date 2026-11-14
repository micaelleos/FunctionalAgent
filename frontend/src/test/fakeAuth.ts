import { vi } from 'vitest'

import type { AuthClient, AuthUser } from '../auth/client'

export const ALICE: AuthUser = {
  uid: 'uid-alice',
  email: 'alice@teste.dev',
  displayName: 'Alice',
  emailVerified: true,
  provider: 'password',
}

/** Dublê do Firebase Auth: guarda o usuário atual e avisa os ouvintes. */
export function fakeAuth(initial: AuthUser | null = null) {
  let user = initial
  const listeners = new Set<(u: AuthUser | null) => void>()
  const set = (next: AuthUser | null) => {
    user = next
    listeners.forEach((l) => l(user))
  }
  const client = {
    onChange: vi.fn((cb: (u: AuthUser | null) => void) => {
      listeners.add(cb)
      queueMicrotask(() => cb(user))
      return () => listeners.delete(cb)
    }),
    signInWithGoogle: vi.fn(async () => set({ ...ALICE, provider: 'google.com' })),
    signInWithEmail: vi.fn(async () => set(ALICE)),
    signUp: vi.fn(async (name: string, email: string) =>
      set({ uid: 'uid-new', email, displayName: name, emailVerified: false, provider: 'password' }),
    ),
    sendPasswordReset: vi.fn(async () => {}),
    resendVerification: vi.fn(async () => {}),
    reload: vi.fn(async () => user),
    getIdToken: vi.fn(async (force: boolean) =>
      user ? `token-${force ? 'novo' : 'atual'}` : null,
    ),
    signOut: vi.fn(async () => set(null)),
  } satisfies AuthClient
  return { client, set, current: () => user }
}
