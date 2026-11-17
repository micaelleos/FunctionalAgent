import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { Alert, PageHeader } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'
import type { JiraProject } from '../product/types'

const AVATAR_COLORS = ['bg-indigo-600', 'bg-teal-700', 'bg-amber-700', 'bg-pink-700', 'bg-blue-700']
const KEY = ['jira-projects']

const codeOf = (error: unknown) =>
  typeof error === 'object' && error !== null && 'code' in error ? String(error.code) : ''

/** Projetos Jira (F09): cards com contagens, busca, "Open in Jira" e atalho para o chat. */
export function ProjectsPage() {
  const product = useProduct()
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const connection = useQuery({ queryKey: ['jira-connection'], queryFn: product.getJiraConnection })
  const projects = useQuery({
    queryKey: KEY,
    queryFn: () => product.listProjects(),
    // Com a conexão inválida, o aviso do layout pede para reconectar (F04-RF-06); nada a buscar.
    enabled: product.features.projects && connection.data?.status === 'ok',
    retry: false,
  })
  // "Refresh" ignora o cache de 5 min do backend (F09-RF-07).
  const refresh = useMutation({
    mutationFn: () => product.listProjects(true),
    onSuccess: (data) => queryClient.setQueryData(KEY, data),
  })
  const error = refresh.error ?? projects.error
  const rejected = codeOf(error) === 'jira-credential-rejected'
  const stale = rejected && connection.data?.status === 'ok'
  useEffect(() => {
    // A API marcou a conexão como inválida (F09-RF-06): recarregada, ela liga o aviso do layout
    // com "Reconnect".
    if (stale) void queryClient.invalidateQueries({ queryKey: ['jira-connection'] })
  }, [stale, queryClient])

  const q = query.trim().toLowerCase()
  const visible = (projects.data ?? []).filter(
    (p) => !q || p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q),
  )
  const ready = product.features.projects && connection.data?.status === 'ok'

  return (
    <main className="flex flex-col gap-6 px-4 py-8 md:px-10">
      <PageHeader
        title={t.projects.title}
        subtitle={projects.data ? t.projects.subtitle(projects.data.length) : undefined}
      >
        {ready && (
          <div className="flex w-full flex-wrap items-end gap-2 sm:w-auto">
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
            <button
              type="button"
              onClick={() => refresh.mutate()}
              disabled={refresh.isPending || projects.isFetching}
              className="min-h-11 rounded-lg border border-zinc-300 bg-white px-4 text-sm hover:bg-zinc-50 disabled:opacity-50"
            >
              {refresh.isPending ? t.projects.refreshing : t.projects.refresh}
            </button>
          </div>
        )}
      </PageHeader>

      {(connection.isPending || projects.isLoading) && (
        <p role="status" className="text-zinc-600">
          {t.common.loading}
        </p>
      )}
      {error && !rejected && <Alert kind="error">{errorMessage(error)}</Alert>}

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

      {product.features.projects &&
        projects.data &&
        !rejected &&
        connection.data?.status === 'ok' && (
          <ul className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
            {visible.map((p, i) => (
              <ProjectCard
                key={p.key}
                project={p}
                color={AVATAR_COLORS[i % AVATAR_COLORS.length]}
              />
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

function Count({ value, label }: { value: number | null; label: string }) {
  return (
    <span>
      {value === null ? (
        <strong className="text-lg text-zinc-900" title={t.projects.unknownCount}>
          <span aria-hidden="true">—</span>
          <span className="sr-only">{t.projects.unknownCount}</span>
        </strong>
      ) : (
        <strong className="text-lg text-zinc-900">{value}</strong>
      )}{' '}
      {label}
    </span>
  )
}

function Avatar({ project, color }: { project: JiraProject; color: string }) {
  const [failed, setFailed] = useState(false)
  if (project.avatarUrl && !failed) {
    return (
      <img
        src={project.avatarUrl}
        alt=""
        width={44}
        height={44}
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className="size-11 shrink-0 rounded-lg"
      />
    )
  }
  // Reserva: iniciais da chave (avatar privado ou fora do ar).
  return (
    <span
      aria-hidden="true"
      data-testid="avatar-iniciais"
      className={`flex size-11 shrink-0 items-center justify-center rounded-lg text-sm font-semibold text-white ${color}`}
    >
      {project.key.slice(0, 2)}
    </span>
  )
}

function ProjectCard({ project: p, color }: { project: JiraProject; color: string }) {
  return (
    <li className="flex flex-col gap-4 rounded-xl border border-zinc-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <Avatar project={p} color={color} />
        <div className="min-w-0">
          <h2 className="truncate font-semibold">{p.name}</h2>
          <p className="text-sm text-zinc-600">
            {p.key} · {t.projects.types[p.type] ?? p.type}
          </p>
        </div>
      </div>
      <p className="flex gap-5 text-sm text-zinc-600">
        <Count value={p.openIssues} label={t.projects.open} />
        <Count value={p.totalIssues} label={t.projects.total} />
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
  )
}
