import { createContext, useContext } from 'react'

import type { AccountApi } from '../lib/api'
import type { AuthClient, AuthUser } from './client'

export type AuthStatus = 'loading' | 'signed-out' | 'unverified' | 'signed-in'

export interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  client: AuthClient
  api: AccountApi
  /** Relê o usuário (ex.: depois de confirmar o e-mail) e devolve se agora está verificado. */
  refresh(): Promise<boolean>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function statusOf(user: AuthUser | null): Exclude<AuthStatus, 'loading'> {
  if (!user) return 'signed-out'
  // Contas de e-mail/senha só entram depois de confirmar o e-mail (F03-RF-02).
  if (user.provider === 'password' && !user.emailVerified) return 'unverified'
  return 'signed-in'
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth fora do AuthProvider')
  return value
}
