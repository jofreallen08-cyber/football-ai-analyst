import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { ApiError } from '../../api/client'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'
import { LoadingBlock } from './LoadingCard'

/** Renders loading / error states for a query, or the children with its data. */
export function QueryState<T>({
  query,
  children,
  rows,
}: {
  query: UseQueryResult<T>
  children: (data: T) => ReactNode
  rows?: number
}) {
  if (query.isPending) return <LoadingBlock rows={rows} />
  if (query.isError) {
    const err = query.error
    if (err instanceof ApiError && err.status === 404) {
      return (
        <EmptyState
          title="Dati non disponibili"
          message={typeof err.problem?.detail === 'string' ? err.problem.detail : err.message}
        />
      )
    }
    return <ErrorState message={err.message} onRetry={() => void query.refetch()} />
  }
  return <>{children(query.data)}</>
}
