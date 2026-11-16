import { Link, Navigate } from 'react-router'

import { useAuth } from '../auth/context'
import { t } from '../i18n/pt-BR'

const L = t.landing
const SOURCE_URL = 'https://github.com/micaelleos/FunctionalAgent'

function Mark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-6 shrink-0">
      <rect x="4" y="4" width="16" height="16" rx="3" transform="rotate(45 12 12)" fill="#4f46e5" />
      <rect x="9" y="9" width="6" height="6" rx="1" transform="rotate(45 12 12)" fill="#fff" />
    </svg>
  )
}

const ctaPrimary =
  'inline-flex min-h-11 items-center justify-center rounded-lg bg-indigo-600 px-5 text-sm font-semibold text-white hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400'
const ctaSecondary =
  'inline-flex min-h-11 items-center justify-center rounded-lg border border-zinc-600 px-5 text-sm font-semibold text-white hover:bg-zinc-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400'

/** Ilustração estática de uma conversa: mostra o fluxo, não dados de ninguém. */
function ExampleChat() {
  return (
    <figure className="w-full min-w-0 max-w-md justify-self-center">
      <div className="flex flex-col gap-3 rounded-2xl border border-zinc-700 bg-zinc-800/70 p-4 text-sm shadow-2xl shadow-indigo-950/40">
        <p className="max-w-[85%] self-end rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-white">
          {L.exampleUser}
        </p>
        <div className="flex flex-col gap-2 rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-zinc-800">
          <p className="font-semibold text-zinc-900">{L.exampleHeading}</p>
          <p>
            {L.exampleStory.map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </p>
          <pre className="rounded-lg whitespace-pre-wrap bg-zinc-100 px-3 py-2 font-mono text-xs leading-relaxed text-zinc-800">
            {L.exampleGherkin.join('\n')}
          </pre>
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2">
            <span className="flex-1 text-xs font-medium text-indigo-950">{L.exampleAction}</span>
            <span className="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white">
              {L.exampleConfirm}
            </span>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-zinc-400">{L.exampleCaption}</figcaption>
    </figure>
  )
}

/** Página inicial pública (F08-RF-11). Quem já entrou vai direto para o chat. */
export function LandingPage() {
  const { status } = useAuth()
  if (status === 'signed-in') return <Navigate to="/chat" replace />

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <div className="bg-zinc-900 text-white">
        <header className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-4 md:px-8">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Mark />
            {t.app.name}
          </Link>
          <nav aria-label={L.nav} className="ml-auto flex items-center gap-2 text-sm">
            <Link to="/sobre" className="hidden px-3 py-2 text-zinc-300 hover:text-white sm:block">
              {t.nav.about}
            </Link>
            <Link to="/login" className="px-3 py-2 text-zinc-300 hover:text-white">
              {L.signIn}
            </Link>
            <Link
              to="/cadastro"
              className="rounded-lg bg-white px-3 py-2 font-semibold text-zinc-900 hover:bg-zinc-200"
            >
              {L.signUp}
            </Link>
          </nav>
        </header>

        <main>
          <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 pt-10 pb-20 md:grid-cols-2 md:px-8 md:pt-16 md:pb-28">
            <div className="flex min-w-0 flex-col items-start gap-6">
              <span className="rounded-full border border-indigo-400/40 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200">
                {L.badge}
              </span>
              <h1 className="text-4xl leading-tight font-bold tracking-tight text-balance md:text-5xl">
                {L.title}
              </h1>
              <p className="max-w-xl text-lg text-zinc-300">{L.lead}</p>
              <div className="flex flex-wrap gap-3">
                <Link to="/cadastro" className={ctaPrimary}>
                  {L.ctaPrimary}
                </Link>
                <Link to="/login" className={ctaSecondary}>
                  {L.ctaSecondary}
                </Link>
              </div>
            </div>
            <ExampleChat />
          </section>
        </main>
      </div>

      <section aria-labelledby="como-funciona" className="mx-auto max-w-6xl px-4 py-20 md:px-8">
        <h2 id="como-funciona" className="text-2xl font-bold md:text-3xl">
          {L.howTitle}
        </h2>
        <ol className="mt-10 grid gap-6 md:grid-cols-3">
          {L.steps.map((step, i) => (
            <li key={step.title} className="flex flex-col gap-3">
              <span
                aria-hidden="true"
                className="flex size-10 items-center justify-center rounded-full bg-indigo-600 font-semibold text-white"
              >
                {i + 1}
              </span>
              <h3 className="text-lg font-semibold">{step.title}</h3>
              <p className="text-zinc-600">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="recursos" className="border-y border-zinc-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-20 md:px-8">
          <h2 id="recursos" className="text-2xl font-bold md:text-3xl">
            {L.featuresTitle}
          </h2>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {L.features.map((f) => (
              <li key={f.title} className="rounded-xl border border-zinc-200 bg-zinc-50 p-6">
                <h3 className="font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-zinc-600">{f.body}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="status" className="mx-auto max-w-6xl px-4 py-20 md:px-8">
        <div className="grid gap-10 md:grid-cols-2">
          <div>
            <h2 id="status" className="text-2xl font-bold md:text-3xl">
              {L.statusTitle}
            </h2>
            <p className="mt-4 text-zinc-600">{L.status}</p>
          </div>
          <div className="flex flex-col items-start gap-4 rounded-2xl bg-zinc-900 p-8 text-white">
            <h2 className="text-xl font-bold">{L.closingTitle}</h2>
            <p className="text-zinc-300">{L.closingBody}</p>
            <Link to="/cadastro" className={ctaPrimary}>
              {L.signUp}
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-zinc-200">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-8 text-sm text-zinc-600 md:px-8">
          <span className="flex items-center gap-2 font-medium text-zinc-900">
            <Mark />
            {t.app.name}
          </span>
          <Link to="/sobre" className="hover:text-zinc-900 hover:underline">
            {L.about}
          </Link>
          <a
            href={SOURCE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-zinc-900 hover:underline"
          >
            {L.source}
          </a>
        </div>
      </footer>
    </div>
  )
}
