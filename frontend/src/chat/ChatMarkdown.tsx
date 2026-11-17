import { type ReactNode, memo, useState } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { t } from '../i18n/en'
import { splitBlocks } from './blocks'
import { safeUrl } from './safeUrl'

/**
 * Markdown das respostas do agente (F08-RF-02, F08-RT-02): GFM (tabelas, listas de tarefa), sem
 * HTML bruto — o `react-markdown` escapa HTML por padrão e aqui não há `rehype-raw`. Links só
 * `http(s)` e `mailto`; os externos abrem em outra aba com `noopener noreferrer`.
 */
export const ChatMarkdown = memo(function ChatMarkdown({ text }: { text: string }) {
  return (
    <div className="chat-markdown flex flex-col gap-3 leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        urlTransform={safeUrl}
        skipHtml
      >
        {text}
      </ReactMarkdown>
    </div>
  )
})

/**
 * A resposta em streaming: um `ChatMarkdown` por bloco, memorizado pelo conteúdo. Só o bloco que
 * ainda cresce é reprocessado a cada quadro (F08-RT-06); a lista solta pode sair partida até a
 * resposta terminar, quando o histórico traz o texto inteiro renderizado de uma vez.
 */
export function StreamingMarkdown({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-3">
      {splitBlocks(text).map((block, i) => (
        <ChatMarkdown key={i} text={block} />
      ))}
    </div>
  )
}

const components: Components = {
  h1: ({ children }) => <h3 className="text-lg font-semibold">{children}</h3>,
  h2: ({ children }) => <h3 className="text-lg font-semibold">{children}</h3>,
  h3: ({ children }) => <h4 className="text-base font-semibold">{children}</h4>,
  h4: ({ children }) => <h4 className="text-base font-semibold">{children}</h4>,
  ul: ({ children }) => <ul className="list-disc pl-6">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-6">{children}</ol>,
  a: ({ href, children }) =>
    href ? (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-indigo-700 underline hover:text-indigo-900"
      >
        {children}
      </a>
    ) : (
      <span>{children}</span>
    ),
  table: ({ children }) => (
    // Tabelas largas rolam na horizontal sem quebrar a página no celular (F08-RF-09).
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={t.chat.table}>
      <table className="min-w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-zinc-300 bg-zinc-100 px-3 py-2 text-left font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="border border-zinc-300 px-3 py-2 align-top">{children}</td>,
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  code: ({ className, children }) =>
    className ? (
      <code className={className}>{children}</code>
    ) : (
      <code className="rounded bg-zinc-100 px-1 font-mono text-[0.9em]">{children}</code>
    ),
}

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (node && typeof node === 'object' && 'props' in node)
    return textOf((node as { props: { children?: ReactNode } }).props.children)
  return ''
}

function CodeBlock({ children }: { children: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(textOf(children).replace(/\n$/, ''))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="flex flex-col gap-2">
      <pre className="overflow-x-auto rounded-lg bg-zinc-900 p-4 font-mono text-sm text-zinc-100">
        {children}
      </pre>
      <button
        type="button"
        onClick={() => void copy()}
        className="min-h-9 self-start rounded-md border border-zinc-300 px-3 text-sm hover:bg-zinc-50"
      >
        {copied ? t.chat.copied : t.chat.copyCode}
      </button>
    </div>
  )
}
