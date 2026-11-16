import type { ReactNode } from 'react'
import { Navigate, type RouteObject } from 'react-router'

import { GuestRoute, ProtectedRoute } from './auth/ProtectedRoute'
import { AppLayout } from './components/AppLayout'
import { PublicLayout } from './components/PublicLayout'
import { AboutPage } from './pages/AboutPage'
import { AccountPage } from './pages/AccountPage'
import { ChatPage } from './pages/ChatPage'
import { IssuesPage } from './pages/IssuesPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { SettingsPage } from './pages/SettingsPage'
import { SignupPage } from './pages/SignupPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

const LEGACY_PATHS: Record<string, string> = {
  '/sobre': '/about',
  '/cadastro': '/signup',
  '/recuperar-senha': '/reset-password',
  '/verificar-email': '/verify-email',
  '/projetos': '/projects',
  '/configuracoes': '/settings',
  '/conta': '/account',
}

const guest = (page: ReactNode) => <GuestRoute>{page}</GuestRoute>

export const routes: RouteObject[] = [
  // Página inicial pública (F08-RF-11), com cabeçalho próprio; quem já entrou vai para o chat.
  { path: '/', element: <LandingPage /> },
  {
    element: <PublicLayout />,
    children: [
      { path: '/about', element: <AboutPage /> },
      { path: '/login', element: guest(<LoginPage />) },
      { path: '/signup', element: guest(<SignupPage />) },
      { path: '/reset-password', element: guest(<ResetPasswordPage />) },
      { path: '/verify-email', element: <VerifyEmailPage /> },
    ],
  },
  {
    // Telas do app (F08-RF-10): todas exigem login (F03-RF-04).
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/chat', element: <ChatPage /> },
      { path: '/chat/:conversationId', element: <ChatPage /> },
      { path: '/projects', element: <ProjectsPage /> },
      { path: '/issues', element: <IssuesPage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '/account', element: <AccountPage /> },
    ],
  },
  // URLs antigas em português (antes do site em inglês): links salvos continuam funcionando.
  ...Object.entries(LEGACY_PATHS).map(([path, to]) => ({
    path,
    element: <Navigate to={to} replace />,
  })),
  { path: '*', element: <Navigate to="/chat" replace /> },
]
