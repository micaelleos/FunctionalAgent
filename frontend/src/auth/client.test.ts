import type { User } from '@firebase/auth'
import { describe, expect, it } from 'vitest'

import { firebaseOptionsFromEnv, toAuthUser } from './client'

describe('F03-RT-08 config do Firebase', () => {
  it('usa a config injetada no build de produção, sem emulador', () => {
    const { options, emulatorHost } = firebaseOptionsFromEnv({
      VITE_FIREBASE_API_KEY: 'chave-publica',
      VITE_FIREBASE_AUTH_DOMAIN: 'pcb-inspect.firebaseapp.com',
      VITE_FIREBASE_PROJECT_ID: 'pcb-inspect',
      VITE_FIREBASE_APP_ID: '1:2:web:3',
    } as ImportMetaEnv)

    expect(options).toEqual({
      apiKey: 'chave-publica',
      authDomain: 'pcb-inspect.firebaseapp.com',
      projectId: 'pcb-inspect',
      appId: '1:2:web:3',
    })
    expect(emulatorHost).toBeNull()
  })

  it('sem config, usa o projeto de demonstração e o emulador local', () => {
    const { options, emulatorHost } = firebaseOptionsFromEnv({} as ImportMetaEnv)

    expect(options.projectId).toBe('demo-functional-agent')
    expect(emulatorHost).toBe('localhost:9099')
  })
})

describe('usuário do Firebase', () => {
  const base = { uid: 'u', email: 'a@b.c', displayName: 'A', emailVerified: false }

  it('conta de senha', () => {
    const user = { ...base, providerData: [{ providerId: 'password' }] } as unknown as User

    expect(toAuthUser(user).provider).toBe('password')
  })

  it('conta federada (Google) prevalece sobre senha', () => {
    const user = {
      ...base,
      providerData: [{ providerId: 'password' }, { providerId: 'google.com' }],
    } as unknown as User

    expect(toAuthUser(user)).toMatchObject({ uid: 'u', provider: 'google.com' })
  })
})
