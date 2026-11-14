import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import {
  assertFails,
  initializeTestEnvironment,
  type RulesTestEnvironment,
} from '@firebase/rules-unit-testing'
import { doc, getDoc, setDoc } from 'firebase/firestore'
import { afterAll, beforeAll, describe, it } from 'vitest'

// Constituição II.2: o cliente nunca acessa o Firestore; só o backend (Admin SDK).
const rules = readFileSync(fileURLToPath(new URL('../../firestore.rules', import.meta.url)), 'utf8')
const [host, port] = (process.env.FIRESTORE_EMULATOR_HOST ?? '127.0.0.1:8081').split(':')

let env: RulesTestEnvironment

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-functional-agent',
    firestore: { rules, host, port: Number(port) },
  })
  await env.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), 'users/alice'), { name: 'Alice' })
  })
})

afterAll(async () => {
  await env.cleanup()
})

describe('AT-F02-04 F02-RT-04 cliente não acessa o Firestore diretamente', () => {
  it('usuário autenticado não lê o próprio users/{uid}', async () => {
    const alice = env.authenticatedContext('alice').firestore()
    await assertFails(getDoc(doc(alice, 'users/alice')))
  })

  it('usuário autenticado não escreve no próprio users/{uid}', async () => {
    const alice = env.authenticatedContext('alice').firestore()
    await assertFails(setDoc(doc(alice, 'users/alice'), { name: 'Mallory' }))
  })

  it('usuário não lê dados de outro usuário', async () => {
    const bob = env.authenticatedContext('bob').firestore()
    await assertFails(getDoc(doc(bob, 'users/alice')))
  })

  it('visitante sem login não lê nem escreve', async () => {
    const anon = env.unauthenticatedContext().firestore()
    await assertFails(getDoc(doc(anon, 'users/alice')))
    await assertFails(setDoc(doc(anon, 'qualquer/coisa'), { x: 1 }))
  })
})
