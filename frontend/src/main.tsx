import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { createFirebaseAuthClient } from './auth/client'
import type { ProductApi } from './product/types'
import { unavailableProductApi } from './product/unavailable'

async function productApi(): Promise<ProductApi> {
  // Dados de demonstração só no servidor de dev (F08-RT-08): `import.meta.env.DEV` é `false` no
  // build, então o Vite remove este ramo e o módulo `demo` nem entra no bundle de produção.
  if (import.meta.env.DEV && import.meta.env.VITE_DEMO_DATA === 'true') {
    const { createDemoProductApi } = await import('./product/demo')
    return createDemoProductApi()
  }
  return unavailableProductApi
}

void productApi().then((api) =>
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App authClient={createFirebaseAuthClient()} productApi={api} />
    </StrictMode>,
  ),
)
