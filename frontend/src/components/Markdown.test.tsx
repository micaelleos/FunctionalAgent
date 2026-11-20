import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Markdown } from './Markdown'

describe('F19-RF-06 links das Referências no cartão', () => {
  it('renderiza [título](https://…) como link em nova aba', () => {
    render(
      <Markdown text={'- [Regras de negócio](https://x.atlassian.net/wiki/spaces/S/pages/1)'} />,
    )
    const link = screen.getByRole('link', { name: 'Regras de negócio' })
    expect(link).toHaveAttribute('href', 'https://x.atlassian.net/wiki/spaces/S/pages/1')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('não vira link sem https', () => {
    render(<Markdown text={'[x](javascript:alert(1)) e [y](http://a.b)'} />)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
