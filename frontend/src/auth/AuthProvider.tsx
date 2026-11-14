import { type ReactNode, useEffect, useMemo, useState } from 'react'

import { createAccountApi } from '../lib/api'
import type { AuthClient, AuthUser } from './client'
import { AuthContext, type AuthContextValue, type AuthStatus, statusOf } from './context'

export function AuthProvider({ client, children }: { client: AuthClient; children: ReactNode }) {
  const [state, setState] = useState<{ status: AuthStatus; user: AuthUser | null }>({
    status: 'loading',
    user: null,
  })

  useEffect(() => client.onChange((user) => setState({ status: statusOf(user), user })), [client])

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      client,
      api: createAccountApi((force) => client.getIdToken(force)),
      refresh: async () => {
        const user = await client.reload()
        const status = statusOf(user)
        setState({ status, user })
        return status === 'signed-in'
      },
    }),
    [state, client],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
