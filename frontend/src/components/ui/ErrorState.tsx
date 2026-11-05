import { AlertTriangle } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorState({ title = 'Si è verificato un errore', message, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border border-danger/40 bg-danger/10 p-4">
      <div className="flex items-center gap-2 text-danger">
        <AlertTriangle className="size-5" aria-hidden="true" />
        <p className="font-semibold">{title}</p>
      </div>
      <p className="text-sm text-ink-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-line bg-navy-800 px-3 py-1.5 text-sm font-medium hover:bg-navy-700"
        >
          Riprova
        </button>
      )}
    </div>
  )
}
