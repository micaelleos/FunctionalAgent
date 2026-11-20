import { Fragment, type ReactNode } from 'react'

/**
 * Markdown mínimo das seções da spec (F06-RF-01): parágrafos, listas `- `, **negrito**,
 * `código` e links `[título](https://…)` (Referências, F19-RF-06). Tudo vira texto do React (escapado); nenhum HTML vindo do agente é interpretado.
 */
export function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter((b) => b.trim())
  return (
    <div className="flex flex-col gap-2">
      {blocks.map((block, i) => {
        const lines = block.split('\n')
        if (lines.every((l) => l.startsWith('- '))) {
          return (
            <ul key={i} className="list-disc pl-5">
              {lines.map((l, j) => (
                <li key={j}>{inline(l.slice(2))}</li>
              ))}
            </ul>
          )
        }
        return (
          <p key={i}>
            {lines.map((l, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {inline(l)}
              </Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}

const TOKEN = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https:\/\/[^\s)]+\))/g
const LINK = /^\[([^\]]+)\]\((https:\/\/[^\s)]+)\)$/

function inline(text: string): ReactNode[] {
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4)
      return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2)
      return (
        <code key={i} className="rounded bg-zinc-100 px-1 text-[0.85em]">
          {part.slice(1, -1)}
        </code>
      )
    const link = LINK.exec(part)
    if (link)
      return (
        <a
          key={i}
          href={link[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-700 underline"
        >
          {link[1]}
        </a>
      )
    return part
  })
}
