/**
 * Divide o Markdown em blocos de topo separados por linha em branco, sem cortar blocos de código
 * cercados (```/~~~). Durante o streaming só o último bloco muda; os anteriores não são
 * reprocessados (F08-RT-06).
 */
export function splitBlocks(text: string): string[] {
  const blocks: string[] = []
  let current: string[] = []
  let fence: string | null = null
  for (const line of text.split('\n')) {
    const marker = /^\s{0,3}(`{3,}|~{3,})/.exec(line)?.[1]
    if (marker && (fence === null || (marker[0] === fence[0] && marker.length >= fence.length)))
      fence = fence === null ? marker : null
    if (fence === null && line.trim() === '' && current.length > 0) {
      blocks.push(current.join('\n'))
      current = []
    } else if (fence !== null || line.trim() !== '') {
      current.push(line)
    }
  }
  if (current.length > 0) blocks.push(current.join('\n'))
  return blocks
}
