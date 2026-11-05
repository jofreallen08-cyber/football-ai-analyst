import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export function Card({ title, action, children, className = '' }: CardProps) {
  return (
    <section className={`rounded-xl border border-line bg-navy-900/80 p-5 shadow-lg shadow-black/20 ${className}`}>
      {(title ?? action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold tracking-wide text-ink-muted uppercase">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  )
}
