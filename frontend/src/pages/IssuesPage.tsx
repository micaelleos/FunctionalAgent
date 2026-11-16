import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { Alert, Button, PageHeader } from '../components/ui'
import { errorMessage, t } from '../i18n/pt-BR'
import { useProduct } from '../product/context'
import type { IssueType } from '../product/types'

const TYPES: IssueType[] = ['Épico', 'História', 'Tarefa']

const STATUS_STYLE: Record<string, string> = {
  'A fazer': 'bg-zinc-100 text-zinc-700',
  'Em andamento': 'bg-blue-100 text-blue-900',
  Concluído: 'bg-green-100 text-green-900',
}

const dateTime = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

/** Issues criadas pelo SpecFlow (tela de F10): filtros, links para o Jira e para a conversa. */
export function IssuesPage() {
  const product = useProduct()
  const queryClient = useQueryClient()
  const [project, setProject] = useState('')
  const [type, setType] = useState<IssueType | ''>('')

  const issues = useQuery({ queryKey: ['issues'], queryFn: product.listIssues })
  const refresh = useMutation({
    mutationFn: product.refreshIssueStatuses,
    onSuccess: (data) => queryClient.setQueryData(['issues'], data),
  })

  const all = issues.data ?? []
  const projects = [...new Set(all.map((i) => i.projectKey))].sort()
  const visible = all.filter(
    (i) => (!project || i.projectKey === project) && (!type || i.type === type),
  )

  return (
    <main className="flex flex-col gap-6 px-4 py-8 md:px-10">
      <PageHeader title={t.issues.title} subtitle={t.issues.subtitle} />

      {issues.isPending && <p className="text-zinc-600">{t.common.loading}</p>}
      {issues.isError && <Alert kind="error">{errorMessage(issues.error)}</Alert>}
      {refresh.isError && <Alert kind="error">{errorMessage(refresh.error)}</Alert>}

      {issues.isSuccess && all.length === 0 && (
        <section className="flex flex-col items-start gap-3 rounded-xl border border-dashed border-zinc-400 bg-white p-6">
          <p className="text-sm text-zinc-700">{t.issues.empty}</p>
          <Link to="/chat" className="text-sm font-medium text-indigo-700 underline">
            {t.issues.goChat}
          </Link>
        </section>
      )}

      {all.length > 0 && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1 text-xs text-zinc-600">
              <label htmlFor="filtro-projeto">{t.issues.project}</label>
              <select
                id="filtro-projeto"
                value={project}
                onChange={(e) => setProject(e.target.value)}
                className="min-h-11 min-w-40 rounded-lg border border-zinc-300 bg-white px-2 text-sm text-zinc-900"
              >
                <option value="">{t.issues.allProjects}</option>
                {projects.map((p) => (
                  <option key={p}>{p}</option>
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
              disabled={refresh.isPending}
              onClick={() => refresh.mutate()}
            >
              {t.issues.refresh}
            </Button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead>
                <tr className="text-left text-xs text-zinc-600">
                  {[
                    t.issues.key,
                    t.issues.type,
                    t.issues.issueTitle,
                    t.issues.status,
                    t.issues.createdAt,
                    t.issues.origin,
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
                {visible.map((i) => (
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
                    </td>
                    <td className="px-4 py-3">{i.type}</td>
                    <td className="px-4 py-3">{i.title}</td>
                    <td className="px-4 py-3">
                      {i.status ? (
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${STATUS_STYLE[i.status] ?? 'bg-zinc-100 text-zinc-700'}`}
                        >
                          {i.status}
                        </span>
                      ) : (
                        <span className="text-zinc-600">{t.issues.statusUnknown}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-zinc-600">
                      {dateTime(i.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/chat/${i.conversationId}`}
                        className="text-indigo-700 hover:underline"
                      >
                        {i.conversationTitle}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visible.length === 0 && (
              <p className="p-6 text-center text-sm text-zinc-600">{t.issues.noMatch}</p>
            )}
          </div>
        </>
      )}
    </main>
  )
}
