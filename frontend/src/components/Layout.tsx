import { Link, NavLink, Outlet, useNavigate } from 'react-router'

import { useAuth } from '../auth/context'
import { t } from '../i18n/pt-BR'

export function Layout() {
  const { status, user, client } = useAuth()
  const navigate = useNavigate()

  const signOut = async () => {
    await client.signOut()
    void navigate('/login', { replace: true })
  }

  const link = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'font-semibold text-sky-800' : 'text-slate-600 hover:text-slate-900'

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <nav className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3" aria-label="Principal">
          <Link to="/" className="flex items-center gap-2 font-semibold text-slate-900">
            {t.app.name}
          </Link>
          {status === 'signed-in' && (
            <NavLink to="/chat" className={link}>
              {t.nav.chat}
            </NavLink>
          )}
          <NavLink to="/sobre" className={link}>
            {t.nav.about}
          </NavLink>
          {status === 'signed-in' && user && (
            <div className="ml-auto flex items-center gap-3" aria-label={t.nav.userMenu}>
              <NavLink to="/conta" className={link}>
                {user.displayName ?? user.email}
              </NavLink>
              <button
                type="button"
                onClick={() => void signOut()}
                className="rounded-md border px-3 py-1 text-sm hover:bg-slate-50"
              >
                {t.nav.signOut}
              </button>
            </div>
          )}
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
