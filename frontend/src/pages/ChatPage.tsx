import { Link } from 'react-router'

import { t } from '../i18n/pt-BR'

export function ChatPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-3 text-2xl font-semibold text-slate-900">{t.chat.title}</h1>
      <p className="text-slate-600">
        {t.chat.soon}{' '}
        <Link to="/conta" className="text-sky-800 underline">
          {t.nav.account}
        </Link>
      </p>
    </main>
  )
}
