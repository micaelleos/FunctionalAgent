import { useQuery } from '@tanstack/react-query'

import { t } from '../i18n/en'
import { useProduct } from '../product/context'

/** Uso do dia e dos últimos 7 dias (tela de F11). Não aparece enquanto o backend não mede o uso. */
export function UsagePanel() {
  const product = useProduct()
  const usage = useQuery({ queryKey: ['usage'], queryFn: product.getUsage })
  if (!usage.data) return null

  const { usedToday, dailyLimit, last7Days } = usage.data
  const max = Math.max(dailyLimit, ...last7Days.map((d) => d.count))

  return (
    <section
      aria-labelledby="uso"
      className="flex flex-col gap-4 rounded-xl border border-zinc-200 bg-white p-6"
    >
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 id="uso" className="flex-1 text-lg font-semibold">
          {t.usage.title}
        </h2>
        <span className="text-sm text-zinc-600">{t.usage.resets}</span>
      </div>
      <div className="flex flex-col gap-2">
        <p className="flex justify-between text-sm">
          <span>{t.usage.today}</span>
          <span>{t.usage.messages(usedToday, dailyLimit)}</span>
        </p>
        <div className="h-2.5 rounded-full bg-zinc-200">
          <div
            className="h-2.5 rounded-full bg-indigo-600"
            style={{ width: `${Math.min(100, (usedToday / dailyLimit) * 100)}%` }}
          />
        </div>
      </div>
      <div
        role="img"
        aria-label={t.usage.chart(last7Days.map((d) => `${d.label} ${d.count}`).join(', '))}
        className="flex h-36 items-end gap-3"
      >
        {last7Days.map((d, i) => (
          <div
            key={d.label}
            className="flex h-full flex-1 flex-col items-center justify-end gap-1.5"
          >
            <span className="text-xs text-zinc-600">{d.count}</span>
            <div
              className={`w-full max-w-12 rounded-t ${i === last7Days.length - 1 ? 'bg-indigo-600' : 'bg-indigo-300'}`}
              style={{ height: `${Math.max(2, (d.count / max) * 90)}px` }}
            />
            <span className="text-xs text-zinc-600">{d.label}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
