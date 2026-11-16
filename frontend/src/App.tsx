import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { createBrowserRouter, createMemoryRouter, RouterProvider } from 'react-router'

import { AuthProvider } from './auth/AuthProvider'
import type { AuthClient } from './auth/client'
import { ProductContext } from './product/context'
import { createHttpProductApi } from './product/http'
import type { ProductApi } from './product/types'
import { routes } from './routes'

export default function App({
  authClient,
  productApi,
  initialPath,
}: {
  authClient: AuthClient
  /** Dados das telas principais; sem ele, a API real (o que ainda não existe fica vazio, F08-RT-08). */
  productApi?: ProductApi
  /** Só nos testes: usa um roteador em memória começando neste caminho. */
  initialPath?: string
}) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
  )
  const [product] = useState(
    () => productApi ?? createHttpProductApi((force) => authClient.getIdToken(force)),
  )
  const [router] = useState(() =>
    initialPath
      ? createMemoryRouter(routes, { initialEntries: [initialPath] })
      : createBrowserRouter(routes),
  )
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={authClient}>
        <ProductContext.Provider value={product}>
          <RouterProvider router={router} />
        </ProductContext.Provider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
