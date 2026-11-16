import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { Alert, PageHeader } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'

const AVATAR_COLORS = ['bg-indigo-600', 'bg-teal-700', 'bg-amber-700', 'bg-pink-700', 'bg-blue-700']

/** Projetos Jira (tela de F09): cards, busca e atalho para conversar sobre o projeto. */
export function ProjectsPage() {
  const product = useProduct()
  const [query, setQuery] = useState('')
  const connection = useQuery({ queryKey: ['jira-connection'], queryFn: product.getJiraConnection })
  const projects = useQuery({
    queryKey: ['jira-projects'],
    queryFn: product.listProjects,
    enabled: product.features.projects && Boolean(connection.data),
  })

  const q = query.trim().toLowerCase()
  const visible = (projects.data ?? []).filter(
    (p) => !q || p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q),
  )

  return (
    <main className="flex flex-col gap-6 px-4 py-8 md:px-10">
      <PageHeader
        title={t.projects.title}
        subtitle={projects.data ? t.projects.subtitle(projects.data.length) : undefined}
      >
        {product.features.projects && connection.data && (
          <div className="flex w-full flex-col gap-1 text-xs text-zinc-600 sm:w-80">
            <label htmlFor="busca-projetos">{t.projects.search}</label>
            <input
              id="busca-projetos"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.projects.searchPlaceholder}
              className="min-h-11 rounded-lg border border-zinc-300 bg-white px-3 text-sm"
            />
          </div>
        )}
      </PageHeader>

      {(connection.isPending || projects.isLoading) && (
        <p className="text-zinc-600">{t.common.loading}</p>
      )}
      {projects.isError && <Alert kind="error">{errorMessage(projects.error)}</Alert>}

      {connection.isSuccess && !connection.data && (
        <section className="flex flex-wrap items-center gap-4 rounded-xl border border-dashed border-zinc-400 bg-white p-6">
          <div className="flex min-w-0 flex-1 basis-80 flex-col gap-1">
            <h2 className="text-lg font-semibold">{t.projects.connectTitle}</h2>
            <p className="text-sm text-zinc-700">{t.projects.connectBody}</p>
          </div>
          <Link
            to="/settings"
            className="inline-flex min-h-11 items-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700"
          >
            {t.projects.connect}
          </Link>
        </section>
      )}

      {connection.data && !product.features.projects && (
        <section className="flex flex-col gap-1 rounded-xl border border-dashed border-zinc-400 bg-white p-6">
          <h2 className="text-lg font-semibold">{t.projects.soonTitle}</h2>
          <p className="text-sm text-zinc-700">{t.projects.soonBody(connection.data.site)}</p>
        </section>
      )}

      {product.features.projects && projects.data && (
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
          {visible.map((p, i) => (
            <li
              key={p.key}
              className="flex flex-col gap-4 rounded-xl border border-zinc-200 bg-white p-5"
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className={`flex size-11 shrink-0 items-center justify-center rounded-lg text-sm font-semibold text-white ${AVATAR_COLORS[i % AVATAR_COLORS.length]}`}
                >
                  {p.key.slice(0, 2)}
                </span>
                <div className="min-w-0">
                  <h2 className="font-semibold">{p.name}</h2>
                  <p className="text-sm text-zinc-600">
                    {p.key} · {p.type}
                  </p>
                </div>
              </div>
              <p className="flex gap-5 text-sm text-zinc-600">
                <span>
                  <strong className="text-lg text-zinc-900">{p.openIssues}</strong>{' '}
                  {t.projects.open}
                </span>
                <span>
                  <strong className="text-lg text-zinc-900">{p.totalIssues}</strong>{' '}
                  {t.projects.total}
                </span>
              </p>
              <div className="mt-auto flex flex-wrap gap-2">
                <Link
                  to={`/chat?projeto=${encodeURIComponent(p.key)}`}
                  className="inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-4 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  {t.projects.chat}
                </Link>
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-11 items-center rounded-lg border border-zinc-300 px-4 text-sm hover:bg-zinc-50"
                >
                  {t.projects.openInJira}
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
      {projects.data && visible.length === 0 && q && (
        <p className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-600">
          {t.projects.noMatch(query.trim())}
        </p>
      )}
    </main>
  )
}
