/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  // Config pública do web app do Firebase (F03-RT-08); injetada pelo `make deploy`.
  readonly VITE_FIREBASE_API_KEY?: string
  readonly VITE_FIREBASE_AUTH_DOMAIN?: string
  readonly VITE_FIREBASE_PROJECT_ID?: string
  readonly VITE_FIREBASE_APP_ID?: string
  readonly VITE_FIREBASE_AUTH_EMULATOR_HOST?: string
  // Dados de demonstração nas telas (F08-RT-08); só vale em `npm run dev`, nunca no build.
  readonly VITE_DEMO_DATA?: string
  /** Site key do reCAPTCHA Enterprise do App Check (F11-RT-07); sem ela, sem App Check. */
  readonly VITE_APPCHECK_SITE_KEY?: string
  /** Versão (commit) do build, para agrupar os erros do front (F11-RT-11). */
  readonly VITE_APP_VERSION?: string
  /** `false` desliga o envio de mensagens (rollback da F08). */
  readonly VITE_FEATURE_CHAT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
