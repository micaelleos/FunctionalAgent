import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { createFirebaseAuthClient } from './auth/client'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App authClient={createFirebaseAuthClient()} />
  </StrictMode>,
)
