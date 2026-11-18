import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { createFirebaseAuthClient } from './auth/client'
import { installErrorReporting } from './lib/errorReporting'
import type { ProductApi } from './product/types'

async function productApi(): Promise<ProductApi | undefined> {
  // Dados de demonstração só no servidor de dev (F08-RT-08): `import.meta.env.DEV` é `false` no
  // build, então o Vite remove este ramo e o módulo `demo` nem entra no bundle de produção.
  if (import.meta.env.DEV && import.meta.env.VITE_DEMO_DATA === 'true') {
    const { createDemoProductApi } = await import('./product/demo')
    return createDemoProductApi()
  }
  return undefined // App usa a API real (createHttpProductApi)
}

installErrorReporting() // F11-RT-11: antes de tudo, para pegar erros do carregamento

void productApi().then((api) =>
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App authClient={createFirebaseAuthClient()} productApi={api} />
    </StrictMode>,
  ),
)
