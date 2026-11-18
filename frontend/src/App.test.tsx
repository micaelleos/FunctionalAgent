import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import App from './App'
import { fakeAuth } from './test/fakeAuth'
import { api, server } from './test/server'

describe('F01-RF-03 status da API no rodapé da página inicial', () => {
  it('exibe "API: ok" e a versão quando /health responde', async () => {
    render(<App authClient={fakeAuth().client} initialPath="/" />)

    expect(await screen.findByText('API: ok')).toBeInTheDocument()
    expect(screen.getByText(/version abc123/)).toBeInTheDocument()
  })

  it('exibe erro quando a API falha', async () => {
    server.use(http.get(api('/health'), () => new HttpResponse(null, { status: 503 })))

    render(<App authClient={fakeAuth().client} initialPath="/" />)

    expect(await screen.findByRole('alert')).toHaveTextContent('API respondeu 503')
  })
})
