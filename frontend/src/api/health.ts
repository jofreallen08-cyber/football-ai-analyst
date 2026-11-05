import { useQuery } from '@tanstack/react-query'

import { apiGet } from './client'

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  environment: string
  database: 'ok' | 'unavailable'
  ai_provider: string
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => apiGet<HealthResponse>('/health', signal),
    refetchInterval: 30_000,
  })
}
