import { Database } from 'lucide-react'

import { formatDate } from '../../lib/format'

interface Props {
  source: string
  attribution?: string | null
  fetchedAt?: string | null
  updatedAt?: string | null
}

export function SourceAttribution({ source, attribution, fetchedAt, updatedAt }: Props) {
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-faint">
      <Database className="size-3.5" aria-hidden="true" />
      <span>
        Fonte: <span className="text-ink-muted">{attribution ?? source}</span>
      </span>
      {fetchedAt && <span>· importato il {formatDate(fetchedAt)}</span>}
      {updatedAt && <span>· aggiornato dalla fonte il {formatDate(updatedAt)}</span>}
    </p>
  )
}
