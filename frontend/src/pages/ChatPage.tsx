import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, type KeyboardEvent, useState } from 'react'
import { Link, NavLink, useNavigate, useParams, useSearchParams } from 'react-router'

import { ActionCard } from '../components/ActionCard'
import { Alert, Button } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'
import type { ChatMessage, MessagePart } from '../product/types'

/**
 * Tela inicial do app (F08): conversas à esquerda, mensagens, cartões de ação e o campo de
 * mensagem. Sem o agente no ar (F05), mostra as sugestões e avisa que o envio chega em breve.
 */
export function ChatPage() {
  const product = useProduct()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { conversationId = null } = useParams()
  const [search] = useSearchParams()
  const [draft, setDraft] = useState('')

  const conversations = useQuery({
    queryKey: ['conversations'],
    queryFn: product.listConversations,
  })
  const messages = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => product.getMessages(conversationId ?? ''),
    enabled: conversationId !== null,
  })

  const current = conversations.data?.find((c) => c.id === conversationId)
  const projectKey = current?.projectKey ?? search.get('projeto')

  const send = useMutation({
    mutationFn: (text: string) => product.sendMessage(conversationId, text, projectKey),
    onSuccess: async ({ conversationId: id }) => {
      // O texto só sai do campo quando o envio dá certo (F08-RF-07).
      setDraft('')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['conversations'] }),
        queryClient.invalidateQueries({ queryKey: ['messages', id] }),
        queryClient.invalidateQueries({ queryKey: ['usage'] }),
      ])
      if (id !== conversationId) void navigate(`/chat/${id}`)
    },
  })

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const text = draft.trim()
    if (text && product.features.chat && !send.isPending) send.mutate(text)
  }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter envia; Shift+Enter quebra a linha (F08-RF-01).
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const list = messages.data ?? []
  const empty = conversationId === null || (messages.isSuccess && list.length === 0)

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
      <aside
        aria-label={t.chat.conversations}
        className="flex max-h-60 shrink-0 flex-col gap-2 overflow-y-auto border-b border-zinc-200 bg-white p-3 lg:max-h-none lg:w-72 lg:border-r lg:border-b-0"
      >
        <Link
          to="/chat"
          className="flex min-h-11 items-center justify-center rounded-lg bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + {t.chat.newConversation}
        </Link>
        {conversations.isSuccess && conversations.data.length === 0 && (
          <p className="px-2 py-3 text-sm text-zinc-600">{t.chat.noConversations}</p>
        )}
        <ul className="flex flex-col gap-1">
          {conversations.data?.map((c) => (
            <li key={c.id}>
              <NavLink
                to={`/chat/${c.id}`}
                className={({ isActive }) =>
                  `flex min-h-11 flex-col justify-center rounded-lg px-3 py-2 ${isActive ? 'bg-indigo-50' : 'hover:bg-zinc-50'}`
                }
              >
                <span className="text-sm font-medium">{c.title}</span>
                <span className="text-xs text-zinc-600">{c.projectKey ?? '—'}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col bg-zinc-50">
        <header className="flex flex-wrap items-center gap-3 border-b border-zinc-200 bg-white px-4 py-4 md:px-8">
          <h1 className="min-w-0 flex-1 text-xl font-semibold">{current?.title ?? t.chat.title}</h1>
          {projectKey && (
            <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-900">
              {t.chat.pinned(projectKey)}
            </span>
          )}
        </header>

        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-8 md:px-8">
          {messages.isError && <Alert kind="error">{errorMessage(messages.error)}</Alert>}
          {empty ? (
            <section className="flex flex-col gap-4 py-8">
              <h2 className="text-2xl font-semibold">{t.chat.emptyTitle}</h2>
              <p className="text-zinc-700">{t.chat.emptyBody}</p>
              <ul className="flex flex-wrap gap-2" aria-label={t.chat.suggestionsLabel}>
                {t.chat.suggestions.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      onClick={() => setDraft(s)}
                      className="min-h-11 rounded-full border border-zinc-300 bg-white px-4 text-sm hover:bg-zinc-100"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            list.map((m) => (
              <Message key={m.id} message={m} conversationId={conversationId ?? ''} />
            ))
          )}
        </div>

        <form
          onSubmit={submit}
          className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-4 pb-6 md:px-8"
        >
          {!product.features.chat && <Alert kind="info">{t.chat.soon}</Alert>}
          {send.isError && <Alert kind="error">{errorMessage(send.error)}</Alert>}
          <div className="flex items-end gap-2 rounded-xl border border-zinc-300 bg-white p-2">
            <label htmlFor="mensagem" className="sr-only">
              {t.chat.messageLabel}
            </label>
            <textarea
              id="mensagem"
              rows={2}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={t.chat.placeholder}
              className="flex-1 resize-none border-0 p-2 outline-none"
            />
            <Button
              type="submit"
              disabled={!product.features.chat || !draft.trim() || send.isPending}
            >
              {t.chat.send}
            </Button>
          </div>
          <p className="text-xs text-zinc-600">{t.chat.guard}</p>
        </form>
      </main>
    </div>
  )
}

function Message({ message, conversationId }: { message: ChatMessage; conversationId: string }) {
  if (message.role === 'user') {
    return (
      <div className="max-w-[80%] self-end rounded-xl rounded-br-sm bg-indigo-600 px-4 py-3 whitespace-pre-wrap text-white">
        <span className="sr-only">{t.chat.you}: </span>
        {message.parts.map((p) => (p.kind === 'text' ? p.text : '')).join('\n')}
      </div>
    )
  }
  const actions = message.parts.filter((p) => p.kind === 'action')
  const tools = message.parts.filter((p) => p.kind === 'tool')
  const body = message.parts.filter((p) => p.kind !== 'action' && p.kind !== 'tool')
  return (
    <div className="flex flex-col gap-3">
      {tools.map((p) => (
        <p
          key={p.label}
          className="self-start rounded-md bg-zinc-200/60 px-3 py-1.5 text-sm text-zinc-700"
        >
          <span aria-hidden="true">✓</span> {p.label}
        </p>
      ))}
      {body.length > 0 && (
        <div className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white px-6 py-5 leading-relaxed">
          <span className="sr-only">{t.chat.assistant}: </span>
          {body.map((p, i) => (
            <Part key={i} part={p} />
          ))}
        </div>
      )}
      {actions.map((p) => (
        <ActionCard key={p.action.id} action={p.action} conversationId={conversationId} />
      ))}
    </div>
  )
}

function Part({ part }: { part: MessagePart }) {
  const [copied, setCopied] = useState(false)
  if (part.kind === 'heading') return <h2 className="text-base font-semibold">{part.text}</h2>
  if (part.kind === 'code') {
    const copy = async () => {
      await navigator.clipboard.writeText(part.text)
      setCopied(true)
    }
    return (
      <div className="flex flex-col gap-2">
        <pre className="overflow-x-auto rounded-lg bg-zinc-900 p-4 font-mono text-sm whitespace-pre-wrap text-zinc-100">
          {part.text}
        </pre>
        <button
          type="button"
          onClick={() => void copy()}
          className="min-h-9 self-start rounded-md border border-zinc-300 px-3 text-sm hover:bg-zinc-50"
        >
          {copied ? t.chat.copied : t.chat.copy}
        </button>
      </div>
    )
  }
  if (part.kind === 'text') return <p>{part.text}</p>
  return null
}
