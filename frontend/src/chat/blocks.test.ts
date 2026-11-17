import { describe, expect, it } from 'vitest'

import { splitBlocks } from './blocks'

describe('F08-RT-06 blocos do streaming', () => {
  it('separa por linha em branco', () => {
    expect(splitBlocks('# Título\n\nParágrafo\nlinha 2\n\n\n- a\n- b')).toEqual([
      '# Título',
      'Parágrafo\nlinha 2',
      '- a\n- b',
    ])
  })

  it('não corta bloco de código, mesmo com linhas em branco ou aberto', () => {
    expect(splitBlocks('Antes\n\n```gherkin\nCenário: a\n\nDado b\n```\n\nDepois')).toEqual([
      'Antes',
      '```gherkin\nCenário: a\n\nDado b\n```',
      'Depois',
    ])
    expect(splitBlocks('```\nx\n\ny')).toEqual(['```\nx\n\ny'])
  })

  it('cerca com ~~~ não fecha com ```', () => {
    expect(splitBlocks('~~~\n```\n\n~~~\n\nfim')).toEqual(['~~~\n```\n\n~~~', 'fim'])
  })
})
