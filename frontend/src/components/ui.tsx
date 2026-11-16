import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

export function Field({
  label,
  id,
  ...input
}: { label: string; id: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="flex flex-col gap-1 text-left">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        className="rounded-md border border-slate-300 px-3 py-2 focus:outline-2 focus:outline-indigo-600"
        {...input}
      />
    </div>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: { variant?: 'primary' | 'secondary' | 'danger' } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
    secondary: 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50',
    danger: 'bg-red-700 text-white hover:bg-red-800',
  }[variant]
  return (
    <button
      className={`min-h-11 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  )
}

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center gap-4 px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      {children}
    </main>
  )
}

export function Alert({ kind, children }: { kind: 'error' | 'info'; children: ReactNode }) {
  return kind === 'error' ? (
    <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
      {children}
    </p>
  ) : (
    <p role="status" className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-950">
      {children}
    </p>
  )
}

/** Cabeçalho das páginas do app: título (h1) e subtítulo. */
export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="flex min-w-0 flex-1 basis-80 flex-col gap-1">
        <h1 className="text-2xl font-semibold text-zinc-900">{title}</h1>
        {subtitle && <p className="text-sm text-zinc-600">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

export function Panel({
  label,
  className = '',
  children,
}: {
  label?: string
  className?: string
  children: ReactNode
}) {
  return (
    <section
      aria-label={label}
      className={`rounded-xl border border-zinc-200 bg-white p-6 ${className}`}
    >
      {children}
    </section>
  )
}
