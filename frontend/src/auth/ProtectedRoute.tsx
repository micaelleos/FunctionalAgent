import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { t } from '../i18n/pt-BR'
import { useAuth } from './context'
import { safeRedirect } from './redirect'

/** Rotas do app exigem login (F03-RF-04); e-mail não confirmado vai para a verificação. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <p className="p-6 text-slate-500">{t.common.loading}</p>
  if (status === 'unverified') return <Navigate to="/verificar-email" replace />
  if (status === 'signed-out') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

/** Telas de login/cadastro: quem já entrou segue para o app. */
export function GuestRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from

  if (status === 'loading') return <p className="p-6 text-slate-500">{t.common.loading}</p>
  if (status === 'signed-in') return <Navigate to={safeRedirect(from)} replace />
  if (status === 'unverified') return <Navigate to="/verificar-email" replace />
  return children
}
