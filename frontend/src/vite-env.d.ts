/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  // Config pública do web app do Firebase (F03-RT-08); injetada pelo `make deploy`.
  readonly VITE_FIREBASE_API_KEY?: string
  readonly VITE_FIREBASE_AUTH_DOMAIN?: string
  readonly VITE_FIREBASE_PROJECT_ID?: string
  readonly VITE_FIREBASE_APP_ID?: string
  readonly VITE_FIREBASE_AUTH_EMULATOR_HOST?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
