import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router'

import { Alert } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'
import type { ConversationSummary } from '../product/types'

const KEY = ['conversations']

/**
 * Conversas na lateral (F08-RF-05): criar (abre uma conversa vazia, gravada no 1º envio), renomear
 * e excluir. As mudanças aparecem na hora (otimistas) e voltam atrás se a API recusar.
 */
export function ConversationSidebar({ currentId }: { currentId: string | null }) {
  const product = useProduct()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const conversations = useQuery({ queryKey: KEY, queryFn: product.listConversations })

  const optimistic = async (change: (list: ConversationSummary[]) => ConversationSummary[]) => {
    await queryClient.cancelQueries({ queryKey: KEY })
    const previous = queryClient.getQueryData<ConversationSummary[]>(KEY)
    queryClient.setQueryData<ConversationSummary[]>(KEY, (list) => change(list ?? []))
    return { previous }
  }
  const rollback = (_e: unknown, _v: unknown, context?: { previous?: ConversationSummary[] }) => {
    if (context?.previous) queryClient.setQueryData(KEY, context.previous)
  }
  const settle = () => queryClient.invalidateQueries({ queryKey: KEY })

  const rename = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      product.renameConversation(id, title),
    onMutate: ({ id, title }) =>
      optimistic((list) => list.map((c) => (c.id === id ? { ...c, title } : c))),
    onError: rollback,
    onSettled: settle,
  })
  const remove = useMutation({
    mutationFn: (id: string) => product.deleteConversation(id),
    onMutate: async (id) => {
      const context = await optimistic((list) => list.filter((c) => c.id !== id))
      if (id === currentId) void navigate('/chat', { replace: true })
      return context
    },
    onError: rollback,
    onSuccess: (_d, id) => queryClient.removeQueries({ queryKey: ['messages', id] }),
    onSettled: settle,
  })

  const error = rename.error ?? remove.error

  return (
    <aside
      aria-label={t.chat.conversations}
      className="flex shrink-0 flex-col gap-2 border-b border-zinc-200 bg-white p-3 lg:w-72 lg:border-r lg:border-b-0"
    >
      <div className="flex gap-2">
        <Link
          to="/chat"
          className="flex min-h-11 flex-1 items-center justify-center rounded-lg bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + {t.chat.newConversation}
        </Link>
        {/* No celular a lista fica recolhida atrás deste botão (F08-RF-09). */}
        <button
          type="button"
          aria-expanded={open}
          aria-controls="lista-de-conversas"
          onClick={() => setOpen(!open)}
          className="min-h-11 rounded-lg border border-zinc-300 px-3 text-sm hover:bg-zinc-50 lg:hidden"
        >
          {open ? t.chat.hideConversations : t.chat.showConversations}
        </button>
      </div>
      {error ? <Alert kind="error">{errorMessage(error)}</Alert> : null}
      <div id="lista-de-conversas" className={`${open ? 'flex' : 'hidden'} flex-col gap-1 lg:flex`}>
        {conversations.isError && <Alert kind="error">{errorMessage(conversations.error)}</Alert>}
        {conversations.isSuccess && conversations.data.length === 0 && (
          <p className="px-2 py-3 text-sm text-zinc-600">{t.chat.noConversations}</p>
        )}
        <ul className="flex flex-col gap-1">
          {conversations.data?.map((c) => (
            <ConversationItem
              key={c.id}
              conversation={c}
              onRename={(title) => rename.mutate({ id: c.id, title })}
              onDelete={() => {
                if (window.confirm(t.chat.deleteConfirm(c.title))) remove.mutate(c.id)
              }}
            />
          ))}
        </ul>
      </div>
    </aside>
  )
}

function ConversationItem({
  conversation,
  onRename,
  onDelete,
}: {
  conversation: ConversationSummary
  onRename: (title: string) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(conversation.title)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const value = title.trim()
    if (value && value !== conversation.title) onRename(value)
    setEditing(false)
  }

  if (editing) {
    return (
      <li>
        <form onSubmit={submit} className="flex flex-col gap-2 rounded-lg bg-zinc-50 p-2">
          <label className="text-xs text-zinc-700" htmlFor={`titulo-${conversation.id}`}>
            {t.chat.newTitle}
          </label>
          <input
            id={`titulo-${conversation.id}`}
            value={title}
            maxLength={80}
            autoFocus
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && setEditing(false)}
            className="min-h-11 rounded-md border border-zinc-300 px-2"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="min-h-9 rounded-md bg-indigo-600 px-3 text-sm text-white hover:bg-indigo-700"
            >
              {t.chat.save}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="min-h-9 rounded-md border border-zinc-300 px-3 text-sm hover:bg-white"
            >
              {t.chat.cancel}
            </button>
          </div>
        </form>
      </li>
    )
  }

  return (
    <li className="group flex items-stretch gap-1">
      <NavLink
        to={`/chat/${conversation.id}`}
        className={({ isActive }) =>
          `flex min-h-11 min-w-0 flex-1 flex-col justify-center rounded-lg px-3 py-2 ${isActive ? 'bg-indigo-50' : 'hover:bg-zinc-50'}`
        }
      >
        <span className="truncate text-sm font-medium">{conversation.title}</span>
        <span className="text-xs text-zinc-600">{conversation.projectKey ?? '—'}</span>
      </NavLink>
      <button
        type="button"
        aria-label={t.chat.renameLabel(conversation.title)}
        title={t.chat.rename}
        onClick={() => {
          setTitle(conversation.title)
          setEditing(true)
        }}
        className="min-h-11 min-w-9 rounded-md text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
      >
        <span aria-hidden="true">✎</span>
      </button>
      <button
        type="button"
        aria-label={t.chat.deleteLabel(conversation.title)}
        title={t.chat.delete}
        onClick={onDelete}
        className="min-h-11 min-w-9 rounded-md text-zinc-600 hover:bg-red-50 hover:text-red-800"
      >
        <span aria-hidden="true">×</span>
      </button>
    </li>
  )
}
