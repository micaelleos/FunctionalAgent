import { defaultUrlTransform } from 'react-markdown'

const SAFE_URL = /^(https?:|mailto:)/i

/** Links das respostas só para `http(s)` e `mailto` (F08-RT-02); o resto perde o `href`. */
export function safeUrl(url: string): string {
  const cleaned = defaultUrlTransform(url)
  return SAFE_URL.test(cleaned) ? cleaned : ''
}
