import { describe, expect, it } from 'vitest'

import { appCheckToken, setAppCheckTokenGetter, withAppCheck } from './appCheck'

describe('F11-RT-07 App Check no SPA', () => {
  it('o SDK do App Check carrega com a versão instalada do @firebase/app', async () => {
    // O SPA importa o App Check sob demanda; uma versão que não bate com o @firebase/app só
    // quebraria no navegador (export ausente). Aqui o import falha no teste.
    const module = await import('@firebase/app-check')
    expect(typeof module.initializeAppCheck).toBe('function')
    expect(typeof module.ReCaptchaEnterpriseProvider).toBe('function')
  })

  it('sem App Check configurado, não manda o cabeçalho', async () => {
    setAppCheckTokenGetter(null)
    expect(await appCheckToken()).toBeNull()
    const headers = await withAppCheck(new Headers({ A: '1' }))
    expect([...headers.keys()]).toEqual(['a'])
  })

  it('com App Check, manda X-Firebase-AppCheck', async () => {
    setAppCheckTokenGetter(async () => 'tok')
    expect((await withAppCheck(new Headers())).get('X-Firebase-AppCheck')).toBe('tok')
    setAppCheckTokenGetter(null)
  })
})
