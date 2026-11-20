import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'

import { ChatMarkdown, StreamingMarkdown } from '../chat/ChatMarkdown'
import { ConversationSidebar } from '../chat/ConversationSidebar'
import { type Turn, useChatStream } from '../chat/useChatStream'
import { ActionCard } from '../components/ActionCard'
import { Alert, Button } from '../components/ui'
import { errorMessage, t } from '../i18n/en'
import { useProduct } from '../product/context'
import type { ChatMessage, ConversationSummary, ProposedAction } from '../product/types'

/**
 * Chat (F08): conversas na lateral, histórico paginado, a resposta em streaming com o indicador de
 * ferramenta e os cartões de ação no fluxo, e o campo de mensagem com "Parar".
 */
export function ChatPage() {
  const product = useProduct()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { conversationId = null } = useParams()
  const [search] = useSearchParams()
  const [draft, setDraft] = useState('')
  const bottom = useRef<HTMLDivElement>(null)

  const conversations = useQuery({
    queryKey: ['conversations'],
    queryFn: product.listConversations,
  })
  const history = useInfiniteQuery({
    queryKey: ['messages', conversationId],
    queryFn: ({ pageParam }) => product.getMessages(conversationId ?? '', pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.nextCursor,
    enabled: conversationId !== null,
  })

  const onConversation = useCallback(
    (id: string) => void navigate(`/chat/${id}`, { replace: true }),
    [navigate],
  )
  const { turn, send, stop, retry, dismiss, busy } = useChatStream({
    onConversation,
    onRestore: setDraft,
  })

  const current = conversations.data?.find((c) => c.id === conversationId)
  const projectKey = conversationId ? (current?.projectKey ?? null) : search.get('projeto')

  const unpin = useMutation({
    mutationFn: (id: string) => product.pinProject(id, null),
    onSuccess: (updated) =>
      queryClient.setQueryData<ConversationSummary[]>(['conversations'], (list) =>
        list?.map((c) => (c.id === updated.id ? updated : c)),
      ),
  })

  // As páginas vêm da mais recente para a mais antiga; na tela, a mais antiga fica em cima.
  const messages = [...(history.data?.pages ?? [])].reverse().flatMap((p) => p.items)
  const visibleTurn =
    turn &&
    turn.conversationId === conversationId &&
    !(turn.messageId && messages.some((m) => m.id === turn.messageId))
      ? turn
      : null
  const empty = messages.length === 0 && !visibleTurn && !history.isLoading

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: 'end' })
  }, [messages.length, visibleTurn?.text, visibleTurn?.actions.length])

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const text = draft.trim()
    if (!text || !product.features.chat || busy) return
    setDraft('')
    void send(conversationId, text, conversationId ? null : projectKey)
  }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter envia; Shift+Enter quebra a linha (F08-RF-01).
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row lg:overflow-hidden">
      <ConversationSidebar currentId={conversationId} />

      <main className="flex min-w-0 flex-1 flex-col bg-zinc-50 lg:min-h-0">
        <header className="flex flex-wrap items-center gap-3 border-b border-zinc-200 bg-white px-4 py-4 md:px-8">
          <h1 className="min-w-0 flex-1 truncate text-xl font-semibold">
            {current?.title ?? t.chat.title}
          </h1>
          {projectKey && (
            <span className="flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-900">
              {t.chat.pinned(projectKey)}
              {conversationId && (
                <button
                  type="button"
                  onClick={() => unpin.mutate(conversationId)}
                  className="rounded-full px-1 text-indigo-900 hover:bg-indigo-100"
                  aria-label={t.chat.unpin}
                  title={t.chat.unpin}
                >
                  <span aria-hidden="true">×</span>
                </button>
              )}
            </span>
          )}
        </header>

        {/* F08: as mensagens rolam dentro deste contêiner (lg+); o campo fica sempre embaixo. `relative`
            prende os rótulos `sr-only` (absolutos) aqui dentro. */}
        <div
          data-testid="chat-scroll"
          className="relative flex flex-1 flex-col lg:min-h-0 lg:overflow-y-auto"
        >
          <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-8 md:px-8">
            {history.isError && <Alert kind="error">{errorMessage(history.error)}</Alert>}
            {history.hasNextPage && (
              <button
                type="button"
                onClick={() => void history.fetchNextPage()}
                disabled={history.isFetchingNextPage}
                className="min-h-11 self-center rounded-full border border-zinc-300 bg-white px-4 text-sm hover:bg-zinc-100 disabled:opacity-50"
              >
                {t.chat.loadEarlier}
              </button>
            )}
            {history.isLoading && conversationId && (
              <p role="status" className="text-sm text-zinc-600">
                {t.chat.loadingHistory}
              </p>
            )}
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
              messages.map((m) => (
                <Message key={m.id} message={m} conversationId={conversationId ?? ''} />
              ))
            )}
            {visibleTurn && (
              <TurnView
                turn={visibleTurn}
                conversationId={conversationId ?? ''}
                onRetry={visibleTurn.started ? retry : () => submit()}
                onDismiss={dismiss}
              />
            )}
            <div ref={bottom} />
          </div>
        </div>

        <form
          onSubmit={submit}
          className="sticky bottom-0 mx-auto flex w-full max-w-3xl flex-col gap-2 bg-zinc-50 px-4 pt-2 pb-6 md:px-8"
        >
          {!product.features.chat && <Alert kind="info">{t.chat.soon}</Alert>}
          <div className="flex items-end gap-2 rounded-xl border border-zinc-300 bg-white p-2 focus-within:ring-2 focus-within:ring-indigo-500">
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
            {busy ? (
              <Button type="button" variant="secondary" onClick={stop}>
                {t.chat.stop}
              </Button>
            ) : (
              <Button type="submit" disabled={!product.features.chat || !draft.trim()}>
                {t.chat.send}
              </Button>
            )}
          </div>
          <p className="text-xs text-zinc-600">{t.chat.guard}</p>
        </form>
      </main>
    </div>
  )
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="max-w-[80%] self-end rounded-xl rounded-br-sm bg-indigo-600 px-4 py-3 whitespace-pre-wrap text-white">
      <span className="sr-only">{t.chat.you}: </span>
      {text}
    </div>
  )
}

function AssistantBubble({
  text,
  actions,
  conversationId,
  interrupted,
  streaming = false,
}: {
  text: string
  actions: ProposedAction[]
  conversationId: string
  interrupted: boolean
  streaming?: boolean
}) {
  return (
    <div className="flex flex-col gap-3">
      {text && (
        <div className="rounded-xl border border-zinc-200 bg-white px-6 py-5">
          <span className="sr-only">{t.chat.assistant}: </span>
          {streaming ? <StreamingMarkdown text={text} /> : <ChatMarkdown text={text} />}
          {interrupted && <p className="mt-3 text-sm text-zinc-600 italic">{t.chat.interrupted}</p>}
        </div>
      )}
      {!text && interrupted && <p className="text-sm text-zinc-600 italic">{t.chat.interrupted}</p>}
      {actions.map((a) => (
        <ActionCard key={a.id} action={a} conversationId={conversationId} />
      ))}
    </div>
  )
}

function Message({ message, conversationId }: { message: ChatMessage; conversationId: string }) {
  if (message.role === 'user') return <UserBubble text={message.text} />
  return (
    <AssistantBubble
      text={message.text}
      actions={message.actions}
      conversationId={conversationId}
      interrupted={message.interrupted}
    />
  )
}

function TurnView({
  turn,
  conversationId,
  onRetry,
  onDismiss,
}: {
  turn: Turn
  conversationId: string
  onRetry: () => void
  onDismiss: () => void
}) {
  // Falhou antes de chegar ao servidor: o texto voltou para o campo, não há balão a mostrar.
  const reachedServer = turn.started || turn.status === 'streaming' || turn.status === 'stopped'
  const failure =
    turn.status === 'failed' || turn.error
      ? turn.error?.code === 'network'
        ? t.chat.networkError
        : turn.error?.code === 'rate-limited'
          ? t.chat.rateLimited(turn.error.retryAfter ?? 10)
          : (t.errors[turn.error?.code ?? ''] ?? turn.error?.message ?? t.chat.agentError)
      : null
  // Cota do dia acabou: tentar de novo não adianta até a renovação (F11-RF-02).
  // Cota do dia e teto mensal do beta só renovam depois: tentar de novo não adianta.
  const canRetry = !['quota-exceeded', 'beta-budget-exhausted'].includes(turn.error?.code ?? '')
  return (
    <>
      {reachedServer && <UserBubble text={turn.userText} />}
      {turn.status === 'streaming' && (
        <p role="status" aria-live="polite" className="self-start text-sm text-zinc-600">
          <span aria-hidden="true" className="mr-2 inline-block animate-pulse">
            ●
          </span>
          {turn.tool ?? (turn.text ? '' : t.chat.thinking)}
        </p>
      )}
      <AssistantBubble
        text={turn.text}
        actions={turn.actions}
        conversationId={conversationId}
        interrupted={turn.status === 'stopped'}
        streaming
      />
      {failure && turn.status !== 'streaming' && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800"
        >
          <span className="flex-1">{failure}</span>
          {canRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="min-h-9 rounded-md bg-red-700 px-3 font-medium text-white hover:bg-red-800"
            >
              {t.chat.retry}
            </button>
          )}
          <button
            type="button"
            onClick={onDismiss}
            className="min-h-9 rounded-md border border-red-300 px-3 hover:bg-red-100"
          >
            {t.chat.cancel}
          </button>
        </div>
      )}
    </>
  )
}
