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
        className="rounded-md border border-slate-300 px-3 py-2 focus:outline-2 focus:outline-sky-600"
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
    primary: 'bg-sky-700 text-white hover:bg-sky-800',
    secondary: 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50',
    danger: 'bg-red-700 text-white hover:bg-red-800',
  }[variant]
  return (
    <button
      className={`rounded-md px-4 py-2 font-medium disabled:opacity-50 ${styles} ${className}`}
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
    <p role="status" className="rounded-md bg-sky-50 px-3 py-2 text-sm text-sky-900">
      {children}
    </p>
  )
}
