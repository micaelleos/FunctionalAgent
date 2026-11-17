import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '../lib/api'
import type { ChatEvent } from '../lib/sse'
import { fromProposedEvent } from '../product/actions'
import { useProduct } from '../product/context'
import type { MessagePage, ProposedAction } from '../product/types'

export type TurnStatus = 'streaming' | 'stopped' | 'failed' | 'done'

/** Falha do turno: `network` (não chegou ao servidor), `api` (Problem Details) ou do agente. */
export interface TurnError {
  code: string
  message: string
}

/** O turno em andamento, mostrado até o histórico relido trazer a resposta gravada. */
export interface Turn {
  conversationId: string | null
  userText: string
  text: string
  /** Resumo da ferramenta em uso ("Checking Jira projects…"), F08-RF-03. */
  tool: string | null
  actions: ProposedAction[]
  status: TurnStatus
  error: TurnError | null
  /** Já chegou algum evento: a mensagem do usuário foi gravada no servidor. */
  started: boolean
  /** Id da resposta gravada (`message_saved`): quando o histórico a trouxer, o turno some. */
  messageId: string | null
}

interface Options {
  /** Conversa criada pelo envio (`id=new`) ou pela fixação do projeto. */
  onConversation?: (conversationId: string) => void
  /** O envio falhou antes de começar: o texto volta para o campo (F08-RF-07). */
  onRestore?: (text: string) => void
}

const frame =
  typeof requestAnimationFrame === 'function'
    ? (cb: () => void) => requestAnimationFrame(cb)
    : (cb: () => void) => setTimeout(cb, 16)

/** Acima disto (≈ 2 mil tokens), a tela atualiza a cada `LONG_FLUSH_MS` em vez de a cada quadro. */
export const LONG_TEXT = 8000
const LONG_FLUSH_MS = 100

/** Espera para reler o histórico depois de "Parar": o servidor grava a parte já enviada. */
export const STOP_REFRESH_MS = 1200

export function useChatStream({ onConversation, onRestore }: Options = {}) {
  const product = useProduct()
  const queryClient = useQueryClient()
  const [turn, setTurn] = useState<Turn | null>(null)
  const controller = useRef<AbortController | null>(null)
  const buffer = useRef('')
  const scheduled = useRef(false)
  const mounted = useRef(true)
  const last = useRef<{ conversationId: string | null; text: string } | null>(null)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const update = useCallback((change: Partial<Turn>) => {
    if (mounted.current) setTurn((t) => (t ? { ...t, ...change } : t))
  }, [])

  // Tokens acumulam no `ref` e vão para a tela no máximo uma vez por quadro; em respostas longas,
  // o bloco final custa mais para reprocessar e a tela atualiza a cada 100 ms (F08-RT-06).
  const flushSoon = useCallback(() => {
    if (scheduled.current) return
    scheduled.current = true
    const flush = () => {
      scheduled.current = false
      update({ text: buffer.current })
    }
    if (buffer.current.length > LONG_TEXT) setTimeout(flush, LONG_FLUSH_MS)
    else frame(flush)
  }, [update])

  const refresh = useCallback(
    async (conversationId: string | null) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['conversations'] }),
        queryClient.invalidateQueries({ queryKey: ['usage'] }),
        conversationId
          ? queryClient.invalidateQueries({ queryKey: ['messages', conversationId] })
          : Promise.resolve(),
      ])
    },
    [queryClient],
  )

  // Se a 1ª busca do histórico de uma conversa nova ainda estava em andamento no fim do turno, o
  // `invalidateQueries` reaproveita essa busca (sem a resposta): o TanStack Query não cancela uma
  // busca que ainda não tem dados. Relê até a resposta gravada aparecer.
  const ensureSaved = useCallback(
    async (conversationId: string | null, messageId: string | null) => {
      if (!conversationId || !messageId) return
      const key = ['messages', conversationId]
      const has = () =>
        queryClient
          .getQueryData<{ pages: MessagePage[] }>(key)
          ?.pages.some((p) => p.items.some((m) => m.id === messageId)) ?? false
      for (let attempt = 0; attempt < 3 && !has(); attempt++) {
        if (!queryClient.getQueryCache().find({ queryKey: key })) return
        // Sem cancelar, o refetch se junta à busca em andamento (sem dados ainda) e não relê.
        await queryClient.cancelQueries({ queryKey: key })
        await queryClient.refetchQueries({ queryKey: key })
      }
    },
    [queryClient],
  )

  const send = useCallback(
    async (conversationId: string | null, text: string, projectKey: string | null = null) => {
      if (controller.current) return
      const abort = new AbortController()
      controller.current = abort
      last.current = { conversationId, text }
      buffer.current = ''
      let current = conversationId
      let started = false
      let savedId: string | null = null
      setTurn({
        conversationId,
        userText: text,
        text: '',
        tool: null,
        actions: [],
        status: 'streaming',
        error: null,
        started: false,
        messageId: null,
      })
      const onEvent = (event: ChatEvent) => {
        if (!started) {
          started = true
          update({ started: true })
        }
        switch (event.event) {
          case 'open':
          case 'message_saved':
            // A conversa existe desde o início do stream: "Parar" antes do fim não a perde.
            if (event.event === 'message_saved') {
              savedId = event.message_id
              update({ messageId: event.message_id })
            }
            if (event.conversation_id !== current) {
              current = event.conversation_id
              update({ conversationId: current })
              if (current !== conversationId) onConversation?.(current)
            }
            break
          case 'token':
            buffer.current += event.text
            flushSoon()
            break
          case 'tool_start':
            update({ tool: event.summary })
            break
          case 'tool_end':
            update({ tool: null })
            break
          case 'action_proposed':
            if (mounted.current)
              setTurn((t) =>
                t ? { ...t, actions: [...t.actions, fromProposedEvent(event, current ?? '')] } : t,
              )
            break
          case 'error':
            update({ error: { code: event.code, message: event.message } })
            break
          case 'done':
            break
        }
      }
      try {
        if (current === null && projectKey) {
          // Projeto fixado antes da 1ª mensagem (F07-RF-06): a conversa nasce com ele.
          current = (await product.createConversation(projectKey)).id
          update({ conversationId: current })
          onConversation?.(current)
        }
        const result = await product.streamMessage(current, text, onEvent, abort.signal)
        current = result.conversationId || current
        update({ text: buffer.current, tool: null, conversationId: current })
        await refresh(current)
        await ensureSaved(current, savedId)
        // Erro do agente (evento `error`): o turno fica na tela com o aviso e "Try again". Sem
        // erro, fica `done` até o histórico trazer a resposta gravada (a tela o esconde então).
        if (mounted.current)
          setTurn((t) =>
            t && t.error
              ? { ...t, status: 'failed' }
              : t?.messageId
                ? { ...t, status: 'done' }
                : null,
          )
      } catch (error) {
        if (abort.signal.aborted) {
          update({ text: buffer.current, tool: null, status: 'stopped' })
          setTimeout(() => {
            void refresh(current).then(() => {
              if (mounted.current) setTurn((t) => (t?.status === 'stopped' ? null : t))
            })
          }, STOP_REFRESH_MS)
        } else {
          const failure: TurnError =
            error instanceof ApiError
              ? { code: error.code, message: error.message }
              : { code: 'network', message: '' }
          update({ text: buffer.current, tool: null, status: 'failed', error: failure })
          if (!started) onRestore?.(text)
          else void refresh(current)
        }
      } finally {
        controller.current = null
      }
    },
    [ensureSaved, flushSoon, onConversation, onRestore, product, refresh, update],
  )

  const stop = useCallback(() => controller.current?.abort(), [])

  /** Tenta de novo o último envio que falhou (F08-RF-07). */
  const retry = useCallback(() => {
    const previous = last.current
    if (!previous) return
    void send(turn?.conversationId ?? previous.conversationId, previous.text)
  }, [send, turn?.conversationId])

  const dismiss = useCallback(() => setTurn(null), [])

  return { turn, send, stop, retry, dismiss, busy: turn?.status === 'streaming' }
}
