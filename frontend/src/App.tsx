import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { createBrowserRouter, createMemoryRouter, RouterProvider } from 'react-router'

import { AuthProvider } from './auth/AuthProvider'
import type { AuthClient } from './auth/client'
import { routes } from './routes'

export default function App({
  authClient,
  initialPath,
}: {
  authClient: AuthClient
  /** Só nos testes: usa um roteador em memória começando neste caminho. */
  initialPath?: string
}) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
  )
  const [router] = useState(() =>
    initialPath
      ? createMemoryRouter(routes, { initialEntries: [initialPath] })
      : createBrowserRouter(routes),
  )
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={authClient}>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  )
}
