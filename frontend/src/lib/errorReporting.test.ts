import { describe, expect, it, vi } from 'vitest'

import {
  type ClientErrorReport,
  installErrorReporting,
  MAX_REPORTS,
  reportRenderError,
} from './errorReporting'

describe('F11-RT-11 erros do front', () => {
  it('relata error, unhandledrejection e render, até 5 por página', () => {
    const sent: ClientErrorReport[] = []
    const uninstall = installErrorReporting({ release: 'abc123', send: (r) => sent.push(r) })

    window.dispatchEvent(new ErrorEvent('error', { error: new TypeError('x is undefined') }))
    const rejection = new Event('unhandledrejection') as PromiseRejectionEvent
    Object.defineProperty(rejection, 'reason', { value: 'falhou' })
    window.dispatchEvent(rejection)
    reportRenderError(new RangeError('render quebrou'))
    for (let i = 0; i < 10; i++) reportRenderError(new Error(`mais ${i}`))
    uninstall()
    reportRenderError(new Error('depois de desinstalar'))

    expect(sent).toHaveLength(MAX_REPORTS)
    expect(sent[0]).toMatchObject({
      kind: 'error',
      message: 'TypeError: x is undefined',
      release: 'abc123',
    })
    expect(sent[0].stack).toContain('TypeError')
    expect(sent[1]).toMatchObject({ kind: 'unhandledrejection', message: 'falhou', stack: '' })
    expect(sent[2]).toMatchObject({ kind: 'render', message: 'RangeError: render quebrou' })
  })

  it('corta mensagens longas', () => {
    const send = vi.fn()
    const uninstall = installErrorReporting({ send })
    reportRenderError(new Error('x'.repeat(2000)))
    uninstall()
    expect(send.mock.calls[0][0].message).toHaveLength(500)
  })
})
