import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'

import { Alert, Button, Field, PageHeader, Panel } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'

const TOKENS_URL = 'https://id.atlassian.com/manage-profile/security/api-tokens'

/** Configurações › Jira (tela de F04): conexão mascarada, trocar e remover, como criar o token. */
export function SettingsPage() {
  const product = useProduct()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ site: '', email: '', token: '' })

  const connection = useQuery({ queryKey: ['jira-connection'], queryFn: product.getJiraConnection })
  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['jira-connection'] }),
      queryClient.invalidateQueries({ queryKey: ['jira-projects'] }),
    ])
  const connect = useMutation({
    mutationFn: product.connectJira,
    onSuccess: async () => {
      setEditing(false)
      setForm({ site: '', email: '', token: '' })
      await invalidate()
    },
  })
  const disconnect = useMutation({ mutationFn: product.disconnectJira, onSuccess: invalidate })
  const validate = useMutation({
    mutationFn: product.validateJira,
    onSuccess: (data) => queryClient.setQueryData(['jira-connection'], data),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    connect.mutate(form)
  }
  const remove = () => {
    if (window.confirm(t.settings.removeConfirm)) disconnect.mutate()
  }

  const startEditing = () => {
    const current = connection.data
    setForm({
      site: current ? `https://${current.site}` : '',
      email: current?.email ?? '',
      token: '',
    })
    validate.reset()
    setEditing(true)
  }

  const showForm = connection.isSuccess && (!connection.data || editing)
  const invalid = connection.data?.status === 'invalid'

  return (
    <main className="flex flex-col gap-6 px-4 py-8 md:px-10">
      <PageHeader title={t.settings.title} subtitle={t.settings.subtitle} />

      <div className="flex flex-wrap items-start gap-6">
        <Panel label={t.settings.panel} className="flex min-w-0 flex-[2_1_480px] flex-col gap-5">
          {connection.isPending && <p className="text-zinc-600">{t.common.loading}</p>}
          {disconnect.isError && <Alert kind="error">{errorMessage(disconnect.error)}</Alert>}

          {connection.data && !editing && (
            <>
              {invalid && (
                <div
                  role="alert"
                  className="flex flex-wrap items-center gap-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-900"
                >
                  <div className="flex min-w-0 flex-1 basis-64 flex-col gap-0.5">
                    <strong>{t.nav.jiraExpiredTitle}</strong>
                    <span>{t.nav.jiraExpiredBody}</span>
                  </div>
                  <Button type="button" onClick={startEditing}>
                    {t.nav.reconnect}
                  </Button>
                </div>
              )}
              {validate.isError && <Alert kind="error">{errorMessage(validate.error)}</Alert>}
              {validate.isSuccess && !invalid && <Alert kind="info">{t.settings.testOk}</Alert>}
              <p className="flex flex-wrap items-center gap-3 text-sm">
                {invalid ? (
                  <span className="inline-flex items-center gap-2 rounded-full bg-red-100 px-3 py-1 font-medium text-red-900">
                    <span aria-hidden="true" className="size-2 rounded-full bg-red-600" />
                    {t.settings.invalid}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 font-medium text-green-900">
                    <span aria-hidden="true" className="size-2 rounded-full bg-green-600" />
                    {t.settings.connectedAs(connection.data.accountName)}
                  </span>
                )}
                <span className="text-zinc-600">
                  {t.settings.validatedAt(
                    new Date(connection.data.validatedAt).toLocaleString('en-US', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    }),
                  )}
                </span>
              </p>
              <dl className="grid gap-4 sm:grid-cols-2">
                {[
                  [t.settings.site, connection.data.site],
                  [t.settings.account, connection.data.accountName],
                  [t.settings.email, connection.data.email],
                  [t.settings.token, `••••••••${connection.data.tokenLast4}`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs text-zinc-600">{label}</dt>
                    <dd className="break-words">{value}</dd>
                  </div>
                ))}
              </dl>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={validate.isPending}
                  onClick={() => validate.mutate()}
                >
                  {t.settings.test}
                </Button>
                <Button type="button" variant="secondary" onClick={startEditing}>
                  {t.settings.replace}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="text-red-700"
                  disabled={disconnect.isPending}
                  onClick={remove}
                >
                  {t.settings.remove}
                </Button>
              </div>
            </>
          )}

          {showForm && (
            <form onSubmit={submit} className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">{t.settings.formTitle}</h2>
              {!product.features.jira && <Alert kind="info">{t.settings.soon}</Alert>}
              <fieldset disabled={!product.features.jira} className="flex flex-col gap-4">
                <Field
                  id="jira-site"
                  label={t.settings.siteLabel}
                  type="url"
                  required
                  placeholder={t.settings.sitePlaceholder}
                  value={form.site}
                  onChange={(e) => setForm({ ...form, site: e.target.value })}
                />
                <Field
                  id="jira-email"
                  label={t.settings.emailLabel}
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
                <Field
                  id="jira-token"
                  label={t.settings.tokenLabel}
                  type="password"
                  required
                  autoComplete="off"
                  aria-describedby="jira-token-hint"
                  value={form.token}
                  onChange={(e) => setForm({ ...form, token: e.target.value })}
                />
                <p id="jira-token-hint" className="-mt-2 text-sm text-zinc-600">
                  {t.settings.tokenHint}
                </p>
                {connect.isError && <Alert kind="error">{errorMessage(connect.error)}</Alert>}
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={connect.isPending}>
                    {t.settings.save}
                  </Button>
                  {connection.data && (
                    <Button type="button" variant="secondary" onClick={() => setEditing(false)}>
                      {t.settings.cancel}
                    </Button>
                  )}
                </div>
              </fieldset>
            </form>
          )}
        </Panel>

        <aside
          aria-labelledby="como-criar-token"
          className="flex min-w-0 flex-[1_1_280px] flex-col gap-3 rounded-xl bg-indigo-50 p-6 text-sm leading-relaxed text-indigo-950"
        >
          <h2 id="como-criar-token" className="text-base font-semibold">
            {t.settings.howTitle}
          </h2>
          <ol className="flex list-decimal flex-col gap-1.5 pl-5">
            {t.settings.howSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <a
            href={TOKENS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-indigo-700 underline"
          >
            {t.settings.howLink}
          </a>
          <p>{t.settings.howNote}</p>
        </aside>
      </div>
    </main>
  )
}
