import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  title: string
  message: string
  icon?: LucideIcon
}

export function EmptyState({ title, message, icon: Icon = Inbox }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-line px-6 py-12 text-center">
      <Icon className="size-10 text-ink-faint" aria-hidden="true" />
      <p className="font-semibold">{title}</p>
      <p className="max-w-md text-sm text-ink-muted">{message}</p>
    </div>
  )
}
