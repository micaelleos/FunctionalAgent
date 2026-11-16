import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'

import { useAuth } from '../auth/context'
import { t } from '../i18n/pt-BR'
import { useProduct } from '../product/context'

const NAV = [
  { to: '/chat', label: t.nav.chat },
  { to: '/projetos', label: t.nav.projects },
  { to: '/issues', label: t.nav.issues },
  { to: '/configuracoes', label: t.nav.settings },
  { to: '/conta', label: t.nav.account },
] as const

/**
 * Layout do app logado (F08-RF-09, F08-RF-10): menu lateral com as telas principais, uso do dia e
 * estado do Jira. Abaixo de 768 px o menu vira uma gaveta aberta pelo botão "Abrir menu".
 */
export function AppLayout() {
  const { user, client } = useAuth()
  const product = useProduct()
  const navigate = useNavigate()
  const location = useLocation()
  const [openPath, setOpenPath] = useState<string | null>(null)
  // A gaveta fecha sozinha ao navegar: só fica aberta no caminho em que foi aberta.
  const open = openPath === location.pathname

  const connection = useQuery({ queryKey: ['jira-connection'], queryFn: product.getJiraConnection })
  const usage = useQuery({ queryKey: ['usage'], queryFn: product.getUsage })

  const signOut = async () => {
    await client.signOut()
    void navigate('/login', { replace: true })
  }

  const link = ({ isActive }: { isActive: boolean }) =>
    `flex min-h-11 items-center rounded-lg px-3 text-sm ${
      isActive
        ? 'bg-zinc-700 font-medium text-white'
        : 'text-zinc-300 hover:bg-zinc-800 hover:text-white'
    }`

  return (
    <div className="flex min-h-screen flex-col bg-zinc-100 text-zinc-900 md:flex-row">
      <div className="flex items-center justify-between bg-zinc-900 px-4 py-2 text-white md:hidden">
        <span className="font-semibold">{t.app.name}</span>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="menu-principal"
          onClick={() => setOpenPath(open ? null : location.pathname)}
          className="min-h-11 rounded-lg px-3 text-sm hover:bg-zinc-800"
        >
          {open ? t.nav.closeMenu : t.nav.openMenu}
        </button>
      </div>

      {/* O fundo escuro acompanha a página inteira; o menu fica fixo no topo ao rolar. */}
      <div className="shrink-0 bg-zinc-900 md:w-60">
        <nav
          id="menu-principal"
          aria-label={t.nav.main}
          className={`${open ? 'flex' : 'hidden'} w-full flex-col gap-1 px-4 py-5 text-zinc-100 md:sticky md:top-0 md:flex md:h-screen`}
        >
          <span className="hidden px-3 pb-5 text-xl font-semibold md:block">{t.app.name}</span>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={link}>
              {item.label}
            </NavLink>
          ))}

          <div className="mt-auto flex flex-col gap-3 px-3 pt-6 text-xs text-zinc-300">
            {usage.data && (
              <div className="flex flex-col gap-2">
                <div className="flex justify-between">
                  <span>{t.nav.usageToday}</span>
                  <span>{t.nav.usageOf(usage.data.usedToday, usage.data.dailyLimit)}</span>
                </div>
                <div className="h-1.5 rounded-full bg-zinc-700">
                  <div
                    className="h-1.5 rounded-full bg-indigo-300"
                    style={{
                      width: `${Math.min(100, (usage.data.usedToday / usage.data.dailyLimit) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            )}
            <span className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`size-2 rounded-full ${
                  !connection.data
                    ? 'bg-zinc-500'
                    : connection.data.status === 'invalid'
                      ? 'bg-red-400'
                      : 'bg-green-400'
                }`}
              />
              {!connection.data
                ? t.nav.jiraDisconnected
                : connection.data.status === 'invalid'
                  ? t.nav.jiraInvalid
                  : t.nav.jiraConnected(connection.data.site)}
            </span>
            {user && (
              <div className="flex items-center gap-2 border-t border-zinc-800 pt-3">
                <NavLink
                  to="/conta"
                  className="min-w-0 flex-1 truncate text-sm text-zinc-100 hover:underline"
                >
                  {user.displayName ?? user.email}
                </NavLink>
                <button
                  type="button"
                  onClick={() => void signOut()}
                  className="min-h-11 rounded-lg px-3 text-sm text-zinc-100 hover:bg-zinc-800"
                >
                  {t.nav.signOut}
                </button>
              </div>
            )}
          </div>
        </nav>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* F04-RF-06: o Jira recusou o token guardado; o aviso aparece em todas as telas. */}
        {connection.data?.status === 'invalid' && location.pathname !== '/configuracoes' && (
          <div
            role="alert"
            className="flex flex-wrap items-center gap-x-4 gap-y-2 bg-red-50 px-4 py-3 text-sm text-red-900 md:px-10"
          >
            <span className="min-w-0 flex-1 basis-64">
              <strong>{t.nav.jiraExpiredTitle}</strong> {t.nav.jiraExpiredBody}
            </span>
            <Link
              to="/configuracoes"
              className="inline-flex min-h-11 items-center rounded-lg bg-red-700 px-4 font-medium text-white hover:bg-red-800"
            >
              {t.nav.reconnect}
            </Link>
          </div>
        )}
        {product.demo && (
          <p role="note" className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-950">
            {t.nav.demo}
          </p>
        )}
        <Outlet />
      </div>
    </div>
  )
}
