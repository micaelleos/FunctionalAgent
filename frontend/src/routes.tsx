import type { ReactNode } from 'react'
import { Navigate, type RouteObject } from 'react-router'

import { GuestRoute, ProtectedRoute } from './auth/ProtectedRoute'
import { AppLayout } from './components/AppLayout'
import { PublicLayout } from './components/PublicLayout'
import { AboutPage } from './pages/AboutPage'
import { AccountPage } from './pages/AccountPage'
import { ChatPage } from './pages/ChatPage'
import { IssuesPage } from './pages/IssuesPage'
import { LoginPage } from './pages/LoginPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { SettingsPage } from './pages/SettingsPage'
import { SignupPage } from './pages/SignupPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

const guest = (page: ReactNode) => <GuestRoute>{page}</GuestRoute>

export const routes: RouteObject[] = [
  {
    element: <PublicLayout />,
    children: [
      { path: '/', element: <Navigate to="/chat" replace /> },
      { path: '/sobre', element: <AboutPage /> },
      { path: '/login', element: guest(<LoginPage />) },
      { path: '/cadastro', element: guest(<SignupPage />) },
      { path: '/recuperar-senha', element: guest(<ResetPasswordPage />) },
      { path: '/verificar-email', element: <VerifyEmailPage /> },
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
      { path: '/projetos', element: <ProjectsPage /> },
      { path: '/issues', element: <IssuesPage /> },
      { path: '/configuracoes', element: <SettingsPage /> },
      { path: '/conta', element: <AccountPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/chat" replace /> },
]
