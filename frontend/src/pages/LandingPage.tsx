import {
  type CSSProperties,
  type ElementType,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react'
import { Link, Navigate } from 'react-router'

import { useAuth } from '../auth/context'
import { t } from '../i18n/pt-BR'

const L = t.landing
const SOURCE_URL = 'https://github.com/micaelleos/FunctionalAgent'

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false
}

function Mark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-6 shrink-0">
      <rect x="4" y="4" width="16" height="16" rx="3" transform="rotate(45 12 12)" fill="#4f46e5" />
      <rect x="9" y="9" width="6" height="6" rx="1" transform="rotate(45 12 12)" fill="#fff" />
    </svg>
  )
}

/**
 * Mostra o conteúdo com um "fade up" quando ele entra na tela. Sem IntersectionObserver (testes,
 * navegadores antigos) ou com movimento reduzido, o conteúdo aparece direto.
 */
function Reveal({
  as: Tag = 'div',
  delay = 0,
  className = '',
  children,
}: {
  as?: ElementType
  delay?: number
  className?: string
  children: ReactNode
}) {
  const ref = useRef<HTMLElement>(null)
  const [visible, setVisible] = useState(
    () => typeof IntersectionObserver === 'undefined' || prefersReducedMotion(),
  )

  useEffect(() => {
    const node = ref.current
    if (visible || !node) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '0px 0px -10% 0px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [visible])

  return (
    <Tag
      ref={ref}
      className={`reveal ${visible ? 'is-visible' : ''} ${className}`}
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      {children}
    </Tag>
  )
}

const ctaPrimary =
  'group inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition duration-200 hover:-translate-y-0.5 hover:bg-indigo-500 hover:shadow-indigo-500/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 active:translate-y-0'
const ctaSecondary =
  'inline-flex min-h-11 items-center justify-center rounded-lg border border-zinc-600 px-5 text-sm font-semibold text-white transition duration-200 hover:-translate-y-0.5 hover:border-zinc-400 hover:bg-zinc-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 active:translate-y-0'

function Arrow() {
  return (
    <span
      aria-hidden="true"
      className="transition-transform duration-200 group-hover:translate-x-1"
    >
      →
    </span>
  )
}

/** Passos da conversa ilustrativa: pergunta, "digitando", história, critérios, ação. */
const STEPS = [600, 1500, 2700, 3700, 4700] as const
const HOLD_MS = 6500

/**
 * Ilustração animada de uma conversa: mostra o fluxo, não dados de ninguém. Toca em laço e, com
 * movimento reduzido, aparece pronta. É decorativa para leitores de tela (a legenda descreve).
 */
function ExampleChat() {
  const [step, setStep] = useState(() => (prefersReducedMotion() ? STEPS.length : 0))

  useEffect(() => {
    if (prefersReducedMotion()) return
    const timers: number[] = []
    const play = () => {
      setStep(0)
      STEPS.forEach((at, i) => timers.push(window.setTimeout(() => setStep(i + 1), at)))
      timers.push(window.setTimeout(play, STEPS[STEPS.length - 1] + HOLD_MS))
    }
    play()
    return () => timers.forEach((id) => window.clearTimeout(id))
  }, [])

  const typing = step === 2
  const answered = step >= 3

  return (
    <figure className="relative w-full max-w-md min-w-0 animate-fade-up justify-self-center [animation-delay:350ms]">
      <div aria-hidden="true" className="motion-safe:animate-float">
        <div className="flex min-h-[25rem] flex-col gap-3 rounded-2xl border border-zinc-700/80 bg-zinc-800/70 p-4 text-sm shadow-2xl shadow-indigo-950/50 backdrop-blur">
          <div className="flex items-center gap-1.5 pb-1">
            <span className="size-2.5 rounded-full bg-zinc-600" />
            <span className="size-2.5 rounded-full bg-zinc-600" />
            <span className="size-2.5 rounded-full bg-zinc-600" />
          </div>

          {step >= 1 && (
            <p className="max-w-[85%] animate-pop-in self-end rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-white">
              {L.exampleUser}
            </p>
          )}

          {typing && (
            <div className="flex w-16 animate-pop-in items-center justify-center gap-1.5 rounded-2xl rounded-bl-sm bg-white px-4 py-3">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className="size-2 animate-typing rounded-full bg-zinc-400"
                  style={{ animationDelay: `${delay}ms` }}
                />
              ))}
            </div>
          )}

          {answered && (
            <div className="flex animate-pop-in flex-col gap-2 rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-zinc-800">
              <p className="font-semibold text-zinc-900">{L.exampleHeading}</p>
              <p>
                {L.exampleStory.map((line, i) => (
                  <span
                    key={line}
                    className="block animate-fade-up"
                    style={{ animationDelay: `${i * 120}ms` }}
                  >
                    {line}
                  </span>
                ))}
              </p>
              {step >= 4 && (
                <pre className="animate-pop-in rounded-lg bg-zinc-100 px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap text-zinc-800">
                  {L.exampleGherkin.map((line, i) => (
                    <span
                      key={line}
                      className="block animate-fade-up"
                      style={{ animationDelay: `${i * 160}ms` }}
                    >
                      {line}
                    </span>
                  ))}
                </pre>
              )}
              {step >= 5 && (
                <div className="flex animate-pop-in flex-wrap items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2">
                  <span className="flex-1 text-xs font-medium text-indigo-950">
                    {L.exampleAction}
                  </span>
                  <span className="animate-ping-soft rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white">
                    {L.exampleConfirm}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-zinc-400">{L.exampleCaption}</figcaption>
    </figure>
  )
}

/** Cabeçalho fixo que ganha fundo e sombra quando a página rola. */
function Header() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`sticky top-0 z-20 text-white transition-[background-color,box-shadow] duration-300 ${
        scrolled ? 'bg-zinc-900/90 shadow-lg shadow-black/20 backdrop-blur-md' : 'bg-transparent'
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-4 md:px-8">
        <Link to="/" className="group flex items-center gap-2 font-semibold">
          <span className="transition-transform duration-500 group-hover:rotate-90">
            <Mark />
          </span>
          {t.app.name}
        </Link>
        <nav aria-label={L.nav} className="ml-auto flex items-center gap-2 text-sm">
          <Link
            to="/sobre"
            className="hidden px-3 py-2 text-zinc-300 transition-colors hover:text-white sm:block"
          >
            {t.nav.about}
          </Link>
          <Link to="/login" className="px-3 py-2 text-zinc-300 transition-colors hover:text-white">
            {L.signIn}
          </Link>
          <Link
            to="/cadastro"
            className="rounded-lg bg-white px-3 py-2 font-semibold text-zinc-900 transition duration-200 hover:-translate-y-0.5 hover:bg-zinc-200"
          >
            {L.signUp}
          </Link>
        </nav>
      </div>
    </header>
  )
}

/** Página inicial pública (F08-RF-11). Quem já entrou vai direto para o chat. */
export function LandingPage() {
  const { status } = useAuth()
  if (status === 'signed-in') return <Navigate to="/chat" replace />

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <Header />
      <div className="relative isolate -mt-[4.5rem] overflow-hidden bg-zinc-900 pt-[4.5rem] text-white">
        {/* Luzes de fundo do topo, só decoração. */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-32 -left-24 size-[28rem] animate-glow rounded-full bg-indigo-600/40 blur-3xl" />
          <div className="absolute top-40 -right-32 size-[24rem] animate-glow rounded-full bg-violet-600/30 blur-3xl [animation-delay:-3s]" />
          <div className="absolute inset-0 bg-[radial-gradient(rgb(255_255_255/0.06)_1px,transparent_1px)] [background-size:24px_24px]" />
        </div>

        <main>
          <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 pt-10 pb-20 md:grid-cols-2 md:px-8 md:pt-16 md:pb-28">
            <div className="flex min-w-0 flex-col items-start gap-6">
              <span className="inline-flex animate-fade-up items-center gap-2 rounded-full border border-indigo-400/40 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200">
                <span aria-hidden="true" className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-indigo-400 opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-indigo-400" />
                </span>
                {L.badge}
              </span>
              <h1 className="animate-fade-up bg-gradient-to-br from-white via-white to-indigo-300 bg-clip-text text-4xl leading-tight font-bold tracking-tight text-balance text-transparent [animation-delay:100ms] md:text-5xl">
                {L.title}
              </h1>
              <p className="max-w-xl animate-fade-up text-lg text-zinc-300 [animation-delay:200ms]">
                {L.lead}
              </p>
              <div className="flex animate-fade-up flex-wrap gap-3 [animation-delay:300ms]">
                <Link to="/cadastro" className={ctaPrimary}>
                  {L.ctaPrimary}
                  <Arrow />
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
        <Reveal>
          <h2 id="como-funciona" className="text-2xl font-bold md:text-3xl">
            {L.howTitle}
          </h2>
        </Reveal>
        <ol className="relative mt-10 grid gap-8 md:grid-cols-3 md:gap-6">
          {L.steps.map((step, i) => (
            <Reveal
              as="li"
              key={step.title}
              delay={i * 150}
              className="relative flex flex-col gap-3"
            >
              {i < L.steps.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute top-5 left-14 hidden h-px w-[calc(100%-2.5rem)] bg-gradient-to-r from-indigo-400 to-indigo-100 md:block"
                />
              )}
              <span
                aria-hidden="true"
                className="flex size-10 items-center justify-center rounded-full bg-indigo-600 font-semibold text-white shadow-lg shadow-indigo-600/30"
              >
                {i + 1}
              </span>
              <h3 className="text-lg font-semibold">{step.title}</h3>
              <p className="text-zinc-600">{step.body}</p>
            </Reveal>
          ))}
        </ol>
      </section>

      <section aria-labelledby="recursos" className="border-y border-zinc-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-20 md:px-8">
          <Reveal>
            <h2 id="recursos" className="text-2xl font-bold md:text-3xl">
              {L.featuresTitle}
            </h2>
          </Reveal>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {L.features.map((f, i) => (
              <Reveal as="li" key={f.title} delay={(i % 3) * 120}>
                <div className="group h-full rounded-xl border border-zinc-200 bg-zinc-50 p-6 transition duration-300 hover:-translate-y-1 hover:border-indigo-200 hover:bg-white hover:shadow-xl hover:shadow-indigo-100">
                  <span
                    aria-hidden="true"
                    className="mb-4 block h-1 w-8 rounded-full bg-indigo-600 transition-all duration-300 group-hover:w-14"
                  />
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm text-zinc-600">{f.body}</p>
                </div>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="status" className="mx-auto max-w-6xl px-4 py-20 md:px-8">
        <div className="grid gap-10 md:grid-cols-2">
          <Reveal>
            <h2 id="status" className="text-2xl font-bold md:text-3xl">
              {L.statusTitle}
            </h2>
            <p className="mt-4 text-zinc-600">{L.status}</p>
          </Reveal>
          <Reveal delay={150}>
            <div className="relative isolate flex flex-col items-start gap-4 overflow-hidden rounded-2xl bg-zinc-900 p-8 text-white">
              <div
                aria-hidden="true"
                className="absolute -right-16 -bottom-20 -z-10 size-64 animate-glow rounded-full bg-indigo-600/40 blur-3xl"
              />
              <h2 className="text-xl font-bold">{L.closingTitle}</h2>
              <p className="text-zinc-300">{L.closingBody}</p>
              <Link to="/cadastro" className={ctaPrimary}>
                {L.signUp}
                <Arrow />
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-zinc-200">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-8 text-sm text-zinc-600 md:px-8">
          <span className="flex items-center gap-2 font-medium text-zinc-900">
            <Mark />
            {t.app.name}
          </span>
          <Link to="/sobre" className="transition-colors hover:text-zinc-900 hover:underline">
            {L.about}
          </Link>
          <a
            href={SOURCE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-zinc-900 hover:underline"
          >
            {L.source}
          </a>
        </div>
      </footer>
    </div>
  )
}
