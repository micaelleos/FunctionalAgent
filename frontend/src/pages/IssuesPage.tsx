import { keepPreviousData, useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { Alert, Button, PageHeader } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'
import type { IssueFilters, IssueStatus, IssueType, IssueReadiness } from '../product/types'

const TYPES: IssueType[] = ['Epic', 'Story', 'Task']
const READINESS: IssueReadiness[] = ['agent_ready', 'human_only', 'not_ready']
const PERIODS = ['all', '7', '30', '90'] as const
type Period = (typeof PERIODS)[number]
/** O backend aceita até 50 chaves por chamada (F10-RT-05). */
const STATUS_CHUNK = 50
const DAY = 24 * 60 * 60 * 1000

const CATEGORY_STYLE: Record<string, string> = {
  new: 'bg-zinc-100 text-zinc-700',
  indeterminate: 'bg-blue-100 text-blue-900',
  done: 'bg-green-100 text-green-900',
}

const READINESS_STYLE: Record<IssueReadiness, string> = {
  agent_ready: 'bg-green-100 text-green-900',
  human_only: 'bg-amber-100 text-amber-900',
  not_ready: 'bg-zinc-100 text-zinc-700',
}

const dateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-US', { dateStyle: 'short', timeStyle: 'short' })

const selectClass =
  'min-h-11 min-w-40 rounded-lg border border-zinc-300 bg-white px-2 text-sm text-zinc-900'

/** Issues criadas ou atualizadas pelo SpecFlow (F10): filtros, links, status e "Copiar para agente". */
export function IssuesPage() {
  const product = useProduct()
  const [project, setProject] = useState('')
  const [type, setType] = useState<IssueType | ''>('')
  const [readiness, setReadiness] = useState<IssueReadiness | ''>('')
  const [period, setPeriod] = useState<Period>('all')
  // O início do período é fixado quando o filtro muda, para a chave da consulta ficar estável.
  const [from, setFrom] = useState<string | undefined>()
  const [statuses, setStatuses] = useState<Record<string, IssueStatus>>({})
  const [copied, setCopied] = useState('')

  const filters: IssueFilters = {
    ...(project && { projectKey: project }),
    ...(type && { type }),
    ...(readiness && { readiness }),
    ...(from && { from }),
  }
  const filtered = Object.keys(filters).length > 0

  const issues = useInfiniteQuery({
    queryKey: ['issues', filters],
    queryFn: ({ pageParam }) => product.listIssues(filters, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.nextCursor,
    // Ao trocar o filtro, a tabela atual fica até a nova página chegar.
    placeholderData: keepPreviousData,
  })
  const connection = useQuery({ queryKey: ['jira-connection'], queryFn: product.getJiraConnection })
  const projects = useQuery({
    queryKey: ['jira-projects'],
    queryFn: () => product.listProjects(),
    enabled: product.features.projects && connection.data?.status === 'ok',
    retry: false,
  })

  const all = issues.data?.pages.flatMap((p) => p.items) ?? []
  const projectKeys = [
    ...new Set([
      ...(projects.data ?? []).map((p) => p.key),
      ...all.map((i) => i.projectKey),
      ...(project ? [project] : []),
    ]),
  ].sort()

  const refresh = useMutation({
    mutationFn: async (keys: string[]) => {
      const found: Record<string, IssueStatus> = {}
      for (let i = 0; i < keys.length; i += STATUS_CHUNK) {
        Object.assign(found, await product.issueStatuses(keys.slice(i, i + STATUS_CHUNK)))
      }
      return found
    },
    onSuccess: (found) => setStatuses((current) => ({ ...current, ...found })),
  })
  const copy = useMutation({
    mutationFn: async (key: string) => {
      const text = await product.agentPrompt(key)
      try {
        await navigator.clipboard.writeText(text)
      } catch {
        throw Object.assign(new Error('clipboard'), { code: 'clipboard-denied' })
      }
      return key
    },
    onMutate: () => setCopied(''),
    onSuccess: (key) => setCopied(t.issues.copied(key)),
  })

  const choosePeriod = (value: Period) => {
    setPeriod(value)
    setFrom(value === 'all' ? undefined : new Date(Date.now() - Number(value) * DAY).toISOString())
  }

  const empty = issues.isSuccess && all.length === 0

  return (
    <main className="flex flex-col gap-6 px-4 py-8 md:px-10">
      <PageHeader title={t.issues.title} subtitle={t.issues.subtitle} />

      {issues.isError && <Alert kind="error">{errorMessage(issues.error)}</Alert>}
      {refresh.isError && <Alert kind="error">{errorMessage(refresh.error)}</Alert>}
      {copy.isError && <Alert kind="error">{errorMessage(copy.error)}</Alert>}
      <p role="status" className="sr-only">
        {copied}
      </p>
      {copied && <p className="text-sm text-green-800">{copied}</p>}

      {empty && !filtered && (
        <section className="flex flex-col items-start gap-3 rounded-xl border border-dashed border-zinc-400 bg-white p-6">
          <p className="text-sm text-zinc-700">{t.issues.empty}</p>
          <Link to="/chat" className="text-sm font-medium text-indigo-700 underline">
            {t.issues.goChat}
          </Link>
        </section>
      )}

      {(all.length > 0 || filtered) && (
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1 text-xs text-zinc-600">
            <label htmlFor="filtro-projeto">{t.issues.project}</label>
            <select
              id="filtro-projeto"
              value={project}
              onChange={(e) => setProject(e.target.value)}
              className={selectClass}
            >
              <option value="">{t.issues.allProjects}</option>
              {projectKeys.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1 text-xs text-zinc-600">
            <label htmlFor="filtro-prontidao">{t.issues.readiness}</label>
            <select
              id="filtro-prontidao"
              value={readiness}
              onChange={(e) => setReadiness(e.target.value as IssueReadiness | '')}
              className={selectClass}
            >
              <option value="">{t.issues.allReadiness}</option>
              {READINESS.map((r) => (
                <option key={r} value={r}>
                  {t.issues.readinessLabel[r]}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1 text-xs text-zinc-600">
            <label htmlFor="filtro-periodo">{t.issues.period}</label>
            <select
              id="filtro-periodo"
              value={period}
              onChange={(e) => choosePeriod(e.target.value as Period)}
              className={selectClass}
            >
              {PERIODS.map((p) => (
                <option key={p} value={p}>
                  {t.issues.periods[p]}
                </option>
              ))}
            </select>
          </div>
          <div role="group" aria-label={t.issues.type} className="flex flex-wrap gap-2">
            {(['', ...TYPES] as const).map((value) => (
              <button
                key={value || 'todos'}
                type="button"
                aria-pressed={type === value}
                onClick={() => setType(value)}
                className={`min-h-11 rounded-lg border px-4 text-sm ${
                  type === value
                    ? 'border-indigo-600 bg-indigo-50 font-medium text-indigo-900'
                    : 'border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50'
                }`}
              >
                {value || t.issues.allTypes}
              </button>
            ))}
          </div>
          <Button
            type="button"
            variant="secondary"
            className="sm:ml-auto"
            disabled={refresh.isPending || all.length === 0}
            onClick={() => refresh.mutate(all.map((i) => i.key))}
          >
            {t.issues.refresh}
          </Button>
        </div>
      )}

      {issues.isPending && <p className="text-zinc-600">{t.common.loading}</p>}

      {(all.length > 0 || (empty && filtered)) && (
        <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
          <table className="w-full min-w-[960px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs text-zinc-600">
                {[
                  t.issues.key,
                  t.issues.type,
                  t.issues.issueTitle,
                  t.issues.readiness,
                  t.issues.status,
                  t.issues.createdAt,
                  t.issues.origin,
                  t.issues.agentColumn,
                ].map((h) => (
                  <th
                    key={h}
                    scope="col"
                    className="border-b border-zinc-200 px-4 py-3 font-semibold"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {all.map((i) => {
                const status = statuses[i.key]
                return (
                  <tr key={i.key} className="border-b border-zinc-100 last:border-0">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <a
                        href={i.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-indigo-700 hover:underline"
                      >
                        {i.key}
                      </a>
                      {i.operation === 'updated' && (
                        <span
                          title={t.issues.updatedOnlyHint}
                          className="ml-2 text-xs text-zinc-600"
                        >
                          {t.issues.updatedOnly}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">{i.type || t.issues.statusUnknown}</td>
                    <td className="px-4 py-3">{i.title}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${READINESS_STYLE[i.readiness]}`}
                      >
                        {t.issues.readinessLabel[i.readiness]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {status ? (
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${CATEGORY_STYLE[status.category] ?? CATEGORY_STYLE.new}`}
                        >
                          {status.name}
                        </span>
                      ) : status === null ? (
                        <span className="text-zinc-600">{t.issues.statusMissing}</span>
                      ) : (
                        <span className="text-zinc-600">{t.issues.statusUnknown}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-zinc-600">
                      {dateTime(i.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      {i.conversationId ? (
                        <Link
                          to={`/chat/${i.conversationId}`}
                          className="text-indigo-700 hover:underline"
                        >
                          {i.conversationTitle || t.issues.origin}
                        </Link>
                      ) : (
                        <span className="text-zinc-600">{t.issues.conversationDeleted}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {i.hasSpec ? (
                        <Button
                          type="button"
                          variant="secondary"
                          aria-label={t.issues.copyLabel(i.key)}
                          disabled={copy.isPending}
                          onClick={() => copy.mutate(i.key)}
                          className="whitespace-nowrap"
                        >
                          {t.issues.copy}
                        </Button>
                      ) : (
                        <span className="text-xs text-zinc-600">{t.issues.noSpec}</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {empty && filtered && (
            <p className="p-6 text-center text-sm text-zinc-600">{t.issues.noMatch}</p>
          )}
        </div>
      )}

      {issues.hasNextPage && (
        <Button
          type="button"
          variant="secondary"
          className="self-center"
          disabled={issues.isFetchingNextPage}
          onClick={() => void issues.fetchNextPage()}
        >
          {t.issues.loadMore}
        </Button>
      )}
    </main>
  )
}
