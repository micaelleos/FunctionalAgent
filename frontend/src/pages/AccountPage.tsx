import { useMutation, useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'

import { useAuth } from '../auth/context'
import { UsagePanel } from '../components/UsagePanel'
import { Alert, Button } from '../components/ui'
import { errorMessage, t } from '../i18n/en'

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function AccountPage() {
  const { user, api, client } = useAuth()
  const navigate = useNavigate()
  const [confirmText, setConfirmText] = useState('')

  const me = useQuery({ queryKey: ['me', user?.uid], queryFn: api.getMe })
  const exporting = useMutation({
    mutationFn: api.exportMe,
    onSuccess: (blob) => download(blob, 'specflow-meus-dados.json'),
  })
  const deleting = useMutation({
    mutationFn: api.deleteMe,
    onSuccess: async () => {
      await client.signOut()
      void navigate('/login', { replace: true, state: { notice: t.account.deleted } })
    },
  })

  const submitDelete = (event: FormEvent) => {
    event.preventDefault()
    if (confirmText === t.account.deleteWord) deleting.mutate()
  }

  return (
    <main className="flex max-w-3xl flex-col gap-8 px-4 py-8 md:px-10">
      <h1 className="text-2xl font-semibold text-slate-900">{t.account.title}</h1>

      <section aria-labelledby="perfil" className="rounded-xl border border-zinc-200 bg-white p-6">
        <h2 id="perfil" className="mb-3 text-lg font-semibold">
          {t.account.profile}
        </h2>
        {me.isPending && <p className="text-slate-500">{t.common.loading}</p>}
        {me.isError && <Alert kind="error">{errorMessage(me.error)}</Alert>}
        {me.data && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-slate-500">{t.account.name}</dt>
            <dd>{me.data.display_name ?? '—'}</dd>
            <dt className="text-slate-500">{t.account.email}</dt>
            <dd>{me.data.email ?? '—'}</dd>
            <dt className="text-slate-500">{t.account.since}</dt>
            <dd>{new Date(me.data.created_at).toLocaleDateString('en-US')}</dd>
          </dl>
        )}
      </section>

      <UsagePanel />

      <section aria-labelledby="dados" className="rounded-xl border border-zinc-200 bg-white p-6">
        <h2 id="dados" className="mb-2 text-lg font-semibold">
          {t.account.exportTitle}
        </h2>
        <p className="mb-3 text-sm text-slate-600">{t.account.exportBody}</p>
        {exporting.isError && <Alert kind="error">{errorMessage(exporting.error)}</Alert>}
        <Button
          type="button"
          variant="secondary"
          disabled={exporting.isPending}
          onClick={() => exporting.mutate()}
        >
          {t.account.exportButton}
        </Button>
      </section>

      <section aria-labelledby="excluir" className="rounded-xl border border-red-200 bg-white p-6">
        <h2 id="excluir" className="mb-2 text-lg font-semibold text-red-800">
          {t.account.deleteTitle}
        </h2>
        <p className="mb-2 text-sm text-slate-700">{t.account.deleteBody}</p>
        <p className="mb-3 text-sm text-slate-700">{t.account.deleteShared}</p>
        {deleting.isError && <Alert kind="error">{errorMessage(deleting.error)}</Alert>}
        <form onSubmit={submitDelete} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex flex-col gap-1">
            <label htmlFor="confirm-delete" className="text-sm font-medium">
              {t.account.deleteConfirmLabel}
            </label>
            <input
              id="confirm-delete"
              autoComplete="off"
              className="rounded-md border border-slate-300 px-3 py-2"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
            />
          </div>
          <Button
            type="submit"
            variant="danger"
            disabled={confirmText !== t.account.deleteWord || deleting.isPending}
          >
            {t.account.deleteButton}
          </Button>
        </form>
      </section>
    </main>
  )
}
