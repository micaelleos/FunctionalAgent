import { Link, NavLink, Outlet, useNavigate } from 'react-router'

import { useAuth } from '../auth/context'
import { t } from '../i18n/en'

/** Layout das páginas públicas (login, cadastro, "Sobre"): cabeçalho simples. */
export function PublicLayout() {
  const { status, user, client } = useAuth()
  const navigate = useNavigate()

  const signOut = async () => {
    await client.signOut()
    void navigate('/login', { replace: true })
  }

  const link = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'font-semibold text-indigo-700' : 'text-zinc-600 hover:text-zinc-900'

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <nav
          className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3"
          aria-label={t.nav.main}
        >
          <Link to="/" className="font-semibold text-zinc-900">
            {t.app.name}
          </Link>
          {status === 'signed-in' && (
            <NavLink to="/chat" className={link}>
              {t.nav.chat}
            </NavLink>
          )}
          <NavLink to="/about" className={link}>
            {t.nav.about}
          </NavLink>
          {status === 'signed-in' && user && (
            <div className="ml-auto flex items-center gap-3" aria-label={t.nav.userMenu}>
              <NavLink to="/account" className={link}>
                {user.displayName ?? user.email}
              </NavLink>
              <button
                type="button"
                onClick={() => void signOut()}
                className="min-h-11 rounded-lg border border-zinc-300 px-3 text-sm hover:bg-zinc-50"
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
