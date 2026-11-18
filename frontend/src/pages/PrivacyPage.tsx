import { t } from '../i18n/en'
import { SUPPORT_URL } from '../lib/links'

/** Página pública de privacidade e uso (F12-RF-04): o que o app guarda, com quem e como apagar. */
export function PrivacyPage() {
  const p = t.privacy
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-16">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{p.title}</h1>
        <p className="text-sm text-slate-500">{p.updated}</p>
        <p className="text-slate-700">{p.intro}</p>
      </header>
      {p.sections.map((section) => (
        <section key={section.title} className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">{section.title}</h2>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-slate-700">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
      <p>
        <a
          href={SUPPORT_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-700 underline"
        >
          {p.contact}
        </a>
      </p>
    </main>
  )
}
