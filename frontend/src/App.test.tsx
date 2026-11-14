import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('F01-RF-03 página de status', () => {
  it('exibe "API: ok" e a versão quando /health responde', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: 'ok', version: 'abc123', env: 'local' }), {
          status: 200,
        }),
      ),
    )

    render(<App />)

    expect(await screen.findByText('API: ok')).toBeInTheDocument()
    expect(screen.getByText(/versão abc123/)).toBeInTheDocument()
  })

  it('exibe erro quando a API falha', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })))

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('API respondeu 503')
  })
})
