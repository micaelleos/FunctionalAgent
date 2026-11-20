import { errorMessage, t } from '../i18n/en'
import type { ActionStatus, PageDiff, ProposedAction } from '../product/types'
import { Markdown } from './Markdown'
import { Alert, Button } from './ui'

/**
 * Cartão de escrita no Confluence (F20-RF-01..04): o que vai para a página, seção por seção, com o
 * antes → depois de uma atualização. Só "Confirm" escreve; "Discard" não envia nada. Se a página
 * mudou depois da proposta, a confirmação falha e nada é sobrescrito.
 */
export function DocActionBody({
  action,
  status,
  busy,
  failure,
  onConfirm,
  onReject,
}: {
  action: ProposedAction
  status: ActionStatus
  busy: boolean
  failure: string | null
  onConfirm: () => void
  onReject: () => void
}) {
  const d = t.chat.doc
  const doc = action.doc
  if (!doc) return null
  const heading =
    action.kind === 'create_space'
      ? d.titleSpace(action.title)
      : action.kind === 'create_page'
        ? d.titleCreate(action.title)
        : d.titleUpdate(action.title)
  const failed =
    action.errorCode === 'confluence-version-conflict'
      ? errorMessage({ code: action.errorCode })
      : `${action.error ?? d.failed} ${t.chat.action.askAgent}`

  return (
    <section
      aria-label={heading}
      className="overflow-hidden rounded-xl border border-teal-200 bg-white"
    >
      <header className="flex flex-wrap items-center gap-2 bg-teal-50 px-5 py-3 text-sm font-semibold text-teal-900">
        <h3 className="flex-1">
          <span className="font-normal text-teal-700">{d.title} · </span>
          {heading}
        </h3>
      </header>
      <dl className="grid gap-x-5 gap-y-3 px-5 py-4 text-sm sm:grid-cols-3">
        {doc.space && (
          <div>
            <dt className="text-xs text-zinc-600">{d.space}</dt>
            <dd>
              <a
                href={doc.space.url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                {doc.space.name}
              </a>{' '}
              · {doc.space.key}
            </dd>
          </div>
        )}
        {action.kind === 'create_space' && (
          <div>
            <dt className="text-xs text-zinc-600">{d.spaceKey}</dt>
            <dd>{doc.spaceKey}</dd>
          </div>
        )}
        {doc.pageType && (
          <div>
            <dt className="text-xs text-zinc-600">{d.pageType}</dt>
            <dd>{d.types[doc.pageType] ?? doc.pageType}</dd>
          </div>
        )}
        {doc.parentTitle && (
          <div>
            <dt className="text-xs text-zinc-600">{d.parent}</dt>
            <dd>{doc.parentTitle}</dd>
          </div>
        )}
        {doc.version !== null && (
          <div>
            <dt className="text-xs text-zinc-600">{d.version}</dt>
            <dd>
              {d.seenVersion(doc.version)}
              {doc.url && (
                <>
                  {' · '}
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="underline">
                    {d.openCurrent}
                  </a>
                </>
              )}
            </dd>
          </div>
        )}
        {doc.previousTitle && (
          <div className="sm:col-span-3">
            <dt className="text-xs text-zinc-600">{d.renamed}</dt>
            <dd>
              <del className="text-zinc-500">{doc.previousTitle}</del> → {action.title}
            </dd>
          </div>
        )}
        {doc.summary && (
          <div className="sm:col-span-3">
            <dt className="text-xs text-zinc-600">{d.summary}</dt>
            <dd>{doc.summary}</dd>
          </div>
        )}
      </dl>

      {action.kind === 'create_space' ? (
        <div className="border-t border-zinc-100 px-5 py-3 text-sm">
          <h4 className="mb-1 font-semibold">{d.pages}</h4>
          <ul className="list-disc pl-5">
            {doc.pages.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      ) : (
        <Diff diff={doc.diff} creating={action.kind === 'create_page'} />
      )}

      <div className="flex flex-col gap-3 border-t border-zinc-100 px-5 py-4">
        {failure && <Alert kind="error">{failure}</Alert>}
        {status === 'pending' && (
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={busy} onClick={onConfirm}>
              {action.kind === 'create_space' ? d.confirmSpace : d.confirm}
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="text-red-700"
              disabled={busy}
              onClick={onReject}
            >
              {d.discard}
            </Button>
          </div>
        )}
        {status === 'executing' && (
          <p role="status" className="text-sm text-zinc-700">
            {d.executing}
          </p>
        )}
        {status === 'done' && (
          <p role="status" className="text-sm text-green-800">
            {d.done}
            {action.resultUrl && (
              <>
                {' · '}
                <a
                  href={action.resultUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-indigo-700 underline"
                >
                  {d.open}
                </a>
              </>
            )}
            {action.warning && <span className="block text-amber-800">{action.warning}</span>}
          </p>
        )}
        {status === 'failed' && (
          <p role="status" className="text-sm text-red-800">
            {failed}
          </p>
        )}
        {status === 'rejected' && (
          <p role="status" className="text-sm text-zinc-700">
            {d.rejected}
          </p>
        )}
        {status === 'expired' && (
          <p role="status" className="text-sm text-zinc-700">
            {t.chat.action.expired}
          </p>
        )}
      </div>
    </section>
  )
}

/** Seções que mudam (F20-RT-04): nova, removida ou antes → depois. */
function Diff({ diff, creating }: { diff: PageDiff[]; creating: boolean }) {
  const d = t.chat.doc
  if (diff.length === 0) return null
  return (
    <details className="border-t border-zinc-100 px-5 py-3 text-sm" open>
      <summary className="cursor-pointer font-medium">{creating ? d.content : d.changes}</summary>
      <div className="mt-3 flex flex-col gap-4">
        {diff.map((s) => (
          <section key={`${s.change}-${s.section}`} aria-label={s.section || d.header}>
            <h4 className="mb-1 font-semibold">
              {s.section || d.header}
              {!creating && (
                <span className="ml-2 rounded bg-zinc-100 px-1.5 py-0.5 text-xs font-normal text-zinc-700">
                  {d.change[s.change]}
                </span>
              )}
            </h4>
            {s.change === 'changed' && (
              <div className="mb-2 rounded bg-red-50 p-2 text-zinc-700" aria-label={d.before}>
                <Markdown text={s.before || '—'} />
              </div>
            )}
            {s.change === 'removed' ? (
              <div className="rounded bg-red-50 p-2 text-zinc-700 line-through">
                <Markdown text={s.before || '—'} />
              </div>
            ) : (
              <div
                className={creating ? '' : 'rounded bg-green-50 p-2'}
                aria-label={creating ? undefined : d.after}
              >
                <Markdown text={s.after || '—'} />
              </div>
            )}
          </section>
        ))}
      </div>
    </details>
  )
}
