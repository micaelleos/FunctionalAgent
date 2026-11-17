import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ChatMarkdown } from './ChatMarkdown'
import { safeUrl } from './safeUrl'

describe('F08-RF-02 Markdown das respostas', () => {
  it('renderiza títulos, listas, tabela e código', () => {
    render(
      <ChatMarkdown
        text={[
          '## Critérios',
          '',
          '- um',
          '- dois',
          '',
          '| CA | Tipo |',
          '|---|---|',
          '| CA-01 | principal |',
          '',
          '```gherkin',
          'Cenário: login',
          '```',
        ].join('\n')}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Critérios' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'CA-01' })).toBeInTheDocument()
    expect(screen.getByText('Cenário: login').closest('pre')).not.toBeNull()
  })

  it('copiar o código leva o texto exato', async () => {
    const user = userEvent.setup() // o setup troca o clipboard; o mock vem depois
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<ChatMarkdown text={'```\nlinha 1\nlinha 2\n```'} />)

    await user.click(screen.getByRole('button', { name: 'Copy code' }))

    expect(writeText).toHaveBeenCalledWith('linha 1\nlinha 2')
    expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument()
  })
})

describe('F08-RT-02 sem HTML do agente', () => {
  it('HTML bruto não vira elemento', () => {
    const { container } = render(
      <ChatMarkdown
        text={'Oi <img src=x onerror="alert(1)"> <script>alert(1)</script> <b>x</b>'}
      />,
    )

    expect(container.querySelector('img, script, b')).toBeNull()
  })

  it('links só http(s) e mailto; externos com rel seguro', () => {
    const { container } = render(
      <ChatMarkdown
        text={
          '[ok](https://jira.example.com/browse/A-1) [ruim](javascript:alert(1)) [dado](data:text/html,x)'
        }
      />,
    )

    const ok = screen.getByRole('link', { name: 'ok' })
    expect(ok).toHaveAttribute('href', 'https://jira.example.com/browse/A-1')
    expect(ok).toHaveAttribute('rel', 'noopener noreferrer')
    expect(ok).toHaveAttribute('target', '_blank')
    expect(screen.queryByRole('link', { name: 'ruim' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'dado' })).toBeNull()
    expect(container.innerHTML).not.toContain('javascript:')
  })

  it('safeUrl', () => {
    expect(safeUrl('mailto:po@teste.dev')).toBe('mailto:po@teste.dev')
    expect(safeUrl('JaVaScRiPt:alert(1)')).toBe('')
    expect(safeUrl('/relativo')).toBe('')
  })
})
