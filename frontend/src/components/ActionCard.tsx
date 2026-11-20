import { useMutation, useQueryClient } from '@tanstack/react-query'

import { errorMessage, t } from '../i18n/en'
import { ActionProblem } from '../product/actions'
import { useProduct } from '../product/context'
import type { ProposedAction } from '../product/types'
import { Markdown } from './Markdown'
import { Alert, Button } from './ui'

/**
 * Cartão de ação proposta (F06-RF-01, F06-RF-06, F06-RF-08; F08-RF-04): mostra exatamente o que
 * vai ao Jira, por seção, com a prontidão para agente de código. Só "Confirmar" escreve; recusar
 * não envia nada. A prontidão avisa e não impede a confirmação.
 */
export function ActionCard({
  action: initial,
  conversationId,
}: {
  action: ProposedAction
  conversationId: string
}) {
  const product = useProduct()
  const queryClient = useQueryClient()
  const onSettled = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['messages', conversationId] }),
      queryClient.invalidateQueries({ queryKey: ['issues'] }),
    ])
  const confirm = useMutation({ mutationFn: product.confirmAction, onSettled })
  const reject = useMutation({ mutationFn: product.rejectAction, onSettled })
  const busy = confirm.isPending || reject.isPending
  const failure = confirm.error ?? reject.error
  // O estado mais novo vem da resposta (ou do erro que traz a ação), não só da lista.
  const action =
    confirm.data ??
    reject.data ??
    (failure instanceof ActionProblem ? failure.action : null) ??
    initial
  const status = confirm.isPending ? 'executing' : action.status
  const creating = action.kind === 'create_issue'
  const a = t.chat.action
  const heading = creating
    ? a.titleCreate(action.issueType ?? 'issue', action.projectKey ?? '')
    : a.titleUpdate(action.issueKey ?? '')

  const fields: [string, string, string?][] = creating
    ? [
        [a.project, [action.projectKey, action.projectName].filter(Boolean).join(' · ')],
        [a.type, action.issueType ?? '—'],
        [a.priority, action.priority ?? a.projectDefault],
        [a.issueTitle, action.title, 'sm:col-span-2'],
        [a.parent, action.parentKey ?? '—'],
        [a.labels, action.labels.join(', ') || '—', 'sm:col-span-3'],
      ]
    : [[a.issue, action.issueKey ?? '—']]

  return (
    <section
      aria-label={heading}
      className="overflow-hidden rounded-xl border border-indigo-200 bg-white"
    >
      <header className="flex flex-wrap items-center gap-2 bg-indigo-50 px-5 py-3 text-sm font-semibold text-indigo-900">
        <h3 className="flex-1">
          <span className="font-normal text-indigo-700">{a.title} · </span>
          {heading}
        </h3>
        {status === 'pending' && (
          <span className="font-normal">
            {a.expires(
              new Date(action.expiresAt).toLocaleString('en-US', {
                dateStyle: 'short',
                timeStyle: 'short',
              }),
            )}
          </span>
        )}
      </header>
      <dl className="grid gap-x-5 gap-y-3 px-5 py-4 text-sm sm:grid-cols-3">
        {fields.map(([label, value, span]) => (
          <div key={label} className={span}>
            <dt className="text-xs text-zinc-600">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>

      <ReadinessBox action={action} />
      <Conflicts action={action} />
      {action.changes.length > 0 && <Changes action={action} />}
      {action.sections.length > 0 && (
        <details className="border-t border-zinc-100 px-5 py-3 text-sm" open={creating}>
          <summary className="cursor-pointer font-medium">{a.spec}</summary>
          <div className="mt-3 flex flex-col gap-4">
            {action.sections.map((s) => (
              <section key={s.title} aria-label={s.title}>
                <h4 className="mb-1 font-semibold">{s.title}</h4>
                <Markdown text={s.markdown} />
              </section>
            ))}
          </div>
        </details>
      )}

      <div className="flex flex-col gap-3 border-t border-zinc-100 px-5 py-4">
        {failure && (!(failure instanceof ActionProblem) || action.status === 'pending') && (
          <Alert kind="error">{problemText(failure)}</Alert>
        )}
        {status === 'pending' && (
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={busy} onClick={() => confirm.mutate(action.id)}>
              {creating ? a.confirm : a.confirmUpdate}
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="text-red-700"
              disabled={busy}
              onClick={() => reject.mutate(action.id)}
            >
              {a.reject}
            </Button>
          </div>
        )}
        {status === 'executing' && (
          <p role="status" className="text-sm text-zinc-700">
            {a.executing}
          </p>
        )}
        {status === 'done' && action.resultKey && (
          <p role="status" className="text-sm text-green-800">
            {creating ? a.created(action.resultKey) : a.updated(action.resultKey)}
            {action.resultUrl && (
              <>
                {' · '}
                <a
                  href={action.resultUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-indigo-700 underline"
                >
                  {a.openInJira}
                </a>
              </>
            )}
          </p>
        )}
        {status === 'failed' && (
          <p role="status" className="text-sm text-red-800">
            {action.error ?? a.failed} {a.askAgent}
          </p>
        )}
        {status === 'rejected' && (
          <p role="status" className="text-sm text-zinc-700">
            {a.rejected}
          </p>
        )}
        {status === 'expired' && (
          <p role="status" className="text-sm text-zinc-700">
            {a.expired}
          </p>
        )}
      </div>
    </section>
  )
}

/** Erros da API sobre ações trazem a mensagem já traduzida (F06-RF-07). */
function problemText(error: unknown): string {
  if (error instanceof ActionProblem) return error.message
  return errorMessage(error)
}

/** Prontidão para agente de código (F06-RF-08): avisa, não bloqueia. */
function ReadinessBox({ action }: { action: ProposedAction }) {
  const readiness = action.readiness
  if (!readiness) return null
  const a = t.chat.action
  const missing = readiness.rules.filter((r) => !r.passed && r.severity === 'obrigatória')
  const warnings = readiness.rules.filter((r) => !r.passed && r.severity !== 'obrigatória')
  const humanOnly = action.labels.includes('human-only')
  return (
    <div
      aria-label={a.readiness}
      role="group"
      className="border-t border-zinc-100 px-5 py-3 text-sm"
    >
      {readiness.ready ? (
        <p className="font-medium text-green-800">{a.ready}</p>
      ) : (
        <>
          <p className="font-medium text-amber-800">{a.notReady}</p>
          <ul className="mt-1 list-disc pl-5 text-amber-900">
            {missing.map((r) => (
              <li key={r.id}>{a.missing(r.label, r.id, r.detail)}</li>
            ))}
          </ul>
        </>
      )}
      {warnings.length > 0 && (
        <ul className="mt-1 list-disc pl-5 text-zinc-700">
          {warnings.map((r) => (
            <li key={r.id}>{a.warning(r.label, r.id, r.detail)}</li>
          ))}
        </ul>
      )}
      {humanOnly && <p className="mt-1 text-zinc-700">{a.humanOnly}</p>}
    </div>
  )
}

/** Conflitos com a documentação do projeto (F19-RF-07): avisa; quem decide é o usuário. */
function Conflicts({ action }: { action: ProposedAction }) {
  if (action.conflicts.length === 0) return null
  const a = t.chat.action
  return (
    <div
      role="group"
      aria-label={a.conflicts}
      className="border-t border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-900"
    >
      <p className="font-medium">{a.conflicts}</p>
      <ul className="mt-1 list-disc pl-5">
        {action.conflicts.map((c) => (
          <li key={c.id}>{a.conflictWith(c.id, c.reason)}</li>
        ))}
      </ul>
    </div>
  )
}

/** Antes → depois dos campos que a atualização muda (F06-RF-06). */
function Changes({ action }: { action: ProposedAction }) {
  const a = t.chat.action
  return (
    <div className="border-t border-zinc-100 px-5 py-3 text-sm">
      <h4 className="mb-2 font-semibold">{a.changes}</h4>
      <dl className="flex flex-col gap-2">
        {action.changes.map((c) =>
          c.field === 'description' ? (
            <div key={c.field}>
              <dt className="text-xs text-zinc-600">{a.fields[c.field]}</dt>
              <dd>
                <details>
                  <summary className="cursor-pointer">{a.descriptionRewritten}</summary>
                  <div className="mt-2 rounded bg-zinc-50 p-2 text-zinc-700">
                    <Markdown text={c.before || '—'} />
                  </div>
                </details>
              </dd>
            </div>
          ) : (
            <div key={c.field}>
              <dt className="text-xs text-zinc-600">{a.fields[c.field]}</dt>
              <dd>
                <del className="text-zinc-500">{c.before || '—'}</del>
                {' → '}
                <ins className="no-underline font-medium">{c.after || '—'}</ins>
              </dd>
            </div>
          ),
        )}
      </dl>
    </div>
  )
}
