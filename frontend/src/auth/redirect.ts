/** Só caminhos internos: evita redirecionamento aberto para outro domínio. */
export function safeRedirect(from: string | undefined): string {
  return from && from.startsWith('/') && !from.startsWith('//') ? from : '/chat'
}
