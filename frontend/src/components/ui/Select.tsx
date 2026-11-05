import type { ReactNode } from 'react'

interface SelectProps {
  label: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
  disabled?: boolean
}

export function Select({ label, value, onChange, children, disabled }: SelectProps) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
      {label}
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 min-w-0 rounded-md border border-line bg-navy-850 px-2.5 text-sm text-ink disabled:opacity-50"
      >
        {children}
      </select>
    </label>
  )
}
