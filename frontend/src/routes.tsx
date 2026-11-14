import { Navigate, type RouteObject } from 'react-router'

import { GuestRoute, ProtectedRoute } from './auth/ProtectedRoute'
import { Layout } from './components/Layout'
import { AboutPage } from './pages/AboutPage'
import { AccountPage } from './pages/AccountPage'
import { ChatPage } from './pages/ChatPage'
import { LoginPage } from './pages/LoginPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { SignupPage } from './pages/SignupPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <Navigate to="/chat" replace /> },
      { path: '/sobre', element: <AboutPage /> },
      {
        path: '/login',
        element: (
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        ),
      },
      {
        path: '/cadastro',
        element: (
          <GuestRoute>
            <SignupPage />
          </GuestRoute>
        ),
      },
      {
        path: '/recuperar-senha',
        element: (
          <GuestRoute>
            <ResetPasswordPage />
          </GuestRoute>
        ),
      },
      { path: '/verificar-email', element: <VerifyEmailPage /> },
      {
        path: '/chat',
        element: (
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/conta',
        element: (
          <ProtectedRoute>
            <AccountPage />
          </ProtectedRoute>
        ),
      },
      { path: '*', element: <Navigate to="/chat" replace /> },
    ],
  },
]
