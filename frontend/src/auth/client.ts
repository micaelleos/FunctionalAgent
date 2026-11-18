import { type FirebaseOptions, initializeApp } from '@firebase/app'
import {
  type Auth,
  connectAuthEmulator,
  createUserWithEmailAndPassword,
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
  type User,
} from '@firebase/auth'

import { setAppCheckTokenGetter } from '../lib/appCheck'

/** Usuário do Firebase Auth reduzido ao que a interface usa. */
export interface AuthUser {
  uid: string
  email: string | null
  displayName: string | null
  emailVerified: boolean
  /** `password` (e-mail e senha) ou o provedor federado, ex. `google.com`. */
  provider: string
}

/** Fronteira com o Firebase Auth; os testes usam um dublê com a mesma interface. */
export interface AuthClient {
  onChange(callback: (user: AuthUser | null) => void): () => void
  signInWithGoogle(): Promise<void>
  signInWithEmail(email: string, password: string): Promise<void>
  signUp(name: string, email: string, password: string): Promise<void>
  sendPasswordReset(email: string): Promise<void>
  resendVerification(): Promise<void>
  /** Relê o usuário no servidor (ex.: depois de confirmar o e-mail). */
  reload(): Promise<AuthUser | null>
  getIdToken(forceRefresh: boolean): Promise<string | null>
  signOut(): Promise<void>
}

export function toAuthUser(user: User): AuthUser {
  const federated = user.providerData.find((p) => p.providerId !== 'password')
  return {
    uid: user.uid,
    email: user.email,
    displayName: user.displayName,
    emailVerified: user.emailVerified,
    provider: federated?.providerId ?? 'password',
  }
}

/**
 * Configuração pública do web app. Em produção vem do `make deploy` (F03-RT-08); sem ela, o app
 * usa o projeto de demonstração dos emuladores (`make dev`, testes E2E).
 */
export function firebaseOptionsFromEnv(env: ImportMetaEnv): {
  options: FirebaseOptions
  emulatorHost: string | null
} {
  if (env.VITE_FIREBASE_API_KEY) {
    return {
      options: {
        apiKey: env.VITE_FIREBASE_API_KEY,
        authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
        projectId: env.VITE_FIREBASE_PROJECT_ID,
        appId: env.VITE_FIREBASE_APP_ID,
      },
      emulatorHost: env.VITE_FIREBASE_AUTH_EMULATOR_HOST ?? null,
    }
  }
  return {
    options: { apiKey: 'demo-key', authDomain: 'localhost', projectId: 'demo-functional-agent' },
    emulatorHost: env.VITE_FIREBASE_AUTH_EMULATOR_HOST ?? 'localhost:9099',
  }
}

export function createFirebaseAuthClient(env: ImportMetaEnv = import.meta.env): AuthClient {
  const { options, emulatorHost } = firebaseOptionsFromEnv(env)
  const app = initializeApp(options)
  const auth: Auth = getAuth(app)
  const siteKey = env.VITE_APPCHECK_SITE_KEY
  if (siteKey && !emulatorHost) {
    // App Check (F11-RT-07) carregado à parte, fora do bundle inicial; as chamadas à API esperam
    // o módulo e pegam um token (renovado sozinho).
    const ready = import('@firebase/app-check').then((m) => ({
      m,
      check: m.initializeAppCheck(app, {
        provider: new m.ReCaptchaEnterpriseProvider(siteKey),
        isTokenAutoRefreshEnabled: true,
      }),
    }))
    setAppCheckTokenGetter(async () => {
      const { m, check } = await ready
      return (await m.getToken(check)).token
    })
  }
  auth.languageCode = 'en'
  if (emulatorHost) {
    connectAuthEmulator(auth, `http://${emulatorHost}`, { disableWarnings: true })
  }

  const current = (): User => {
    if (!auth.currentUser) throw Object.assign(new Error('no session'), { code: 'unauthenticated' })
    return auth.currentUser
  }

  return {
    onChange: (callback) => onAuthStateChanged(auth, (u) => callback(u ? toAuthUser(u) : null)),
    signInWithGoogle: async () => {
      await signInWithPopup(auth, new GoogleAuthProvider())
    },
    signInWithEmail: async (email, password) => {
      await signInWithEmailAndPassword(auth, email, password)
    },
    signUp: async (name, email, password) => {
      const { user } = await createUserWithEmailAndPassword(auth, email, password)
      await updateProfile(user, { displayName: name })
      await sendEmailVerification(user)
    },
    sendPasswordReset: (email) => sendPasswordResetEmail(auth, email),
    resendVerification: () => sendEmailVerification(current()),
    reload: async () => {
      if (!auth.currentUser) return null
      await auth.currentUser.reload()
      // Força um token novo para o backend enxergar email_verified = true.
      await auth.currentUser.getIdToken(true)
      return toAuthUser(auth.currentUser)
    },
    getIdToken: async (forceRefresh) => auth.currentUser?.getIdToken(forceRefresh) ?? null,
    signOut: () => signOut(auth),
  }
}
