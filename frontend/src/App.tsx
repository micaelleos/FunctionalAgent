import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { createBrowserRouter, createMemoryRouter, RouterProvider } from 'react-router'

import { AuthProvider } from './auth/AuthProvider'
import type { AuthClient } from './auth/client'
import { ProductContext } from './product/context'
import type { ProductApi } from './product/types'
import { unavailableProductApi } from './product/unavailable'
import { routes } from './routes'

export default function App({
  authClient,
  productApi = unavailableProductApi,
  initialPath,
}: {
  authClient: AuthClient
  /** Dados das telas principais; em produção, só o que já existe no backend (F08-RT-08). */
  productApi?: ProductApi
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
        <ProductContext.Provider value={productApi}>
          <RouterProvider router={router} />
        </ProductContext.Provider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
