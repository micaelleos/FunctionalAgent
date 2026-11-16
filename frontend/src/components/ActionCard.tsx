import { useMutation, useQueryClient } from '@tanstack/react-query'

import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'
import type { ProposedAction } from '../product/types'
import { Alert, Button } from './ui'

/**
 * Cartão de ação proposta (F08-RF-04, F06): mostra o que vai ao Jira e só cria depois de
 * "Confirmar e criar". Rejeitar não envia nada.
 */
export function ActionCard({
  action,
  conversationId,
}: {
  action: ProposedAction
  conversationId: string
}) {
  const product = useProduct()
  const queryClient = useQueryClient()
  const onDone = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['messages', conversationId] }),
      queryClient.invalidateQueries({ queryKey: ['issues'] }),
    ])
  const confirm = useMutation({ mutationFn: product.confirmAction, onSuccess: onDone })
  const reject = useMutation({ mutationFn: product.rejectAction, onSuccess: onDone })
  const busy = confirm.isPending || reject.isPending
  const failure = confirm.error ?? reject.error

  const fields: [string, string, string?][] = [
    [t.chat.action.project, `${action.projectKey} · ${action.projectName}`],
    [t.chat.action.type, action.issueType],
    [t.chat.action.priority, action.priority],
    [t.chat.action.issueTitle, action.title, 'sm:col-span-2'],
    [t.chat.action.parent, action.parentKey ?? '—'],
  ]

  return (
    <section
      aria-label={t.chat.action.title}
      className="overflow-hidden rounded-xl border border-indigo-200 bg-white"
    >
      <header className="flex flex-wrap items-center gap-2 bg-indigo-50 px-5 py-3 text-sm font-semibold text-indigo-900">
        <h3 className="flex-1">{t.chat.action.title}</h3>
        {action.status === 'pending' && (
          <span className="font-normal">
            {t.chat.action.expires(
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
      <div className="flex flex-col gap-3 px-5 pb-4">
        {failure && <Alert kind="error">{errorMessage(failure)}</Alert>}
        {action.status === 'pending' && (
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={busy} onClick={() => confirm.mutate(action.id)}>
              {t.chat.action.confirm}
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="text-red-700"
              disabled={busy}
              onClick={() => reject.mutate(action.id)}
            >
              {t.chat.action.reject}
            </Button>
          </div>
        )}
        {action.status === 'confirmed' && action.resultKey && (
          <p role="status" className="text-sm text-green-800">
            {t.chat.action.created(action.resultKey)}
            {action.resultUrl && (
              <>
                {' · '}
                <a
                  href={action.resultUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-indigo-700 underline"
                >
                  {t.chat.action.openInJira}
                </a>
              </>
            )}
          </p>
        )}
        {action.status === 'rejected' && (
          <p role="status" className="text-sm text-zinc-700">
            {t.chat.action.rejected}
          </p>
        )}
        {action.status === 'expired' && (
          <p role="status" className="text-sm text-zinc-700">
            {t.chat.action.expired}
          </p>
        )}
      </div>
    </section>
  )
}
