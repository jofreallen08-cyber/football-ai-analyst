/**
 * Minimal typed HTTP client for the backend API.
 *
 * Only the API base URL is configurable; no credentials ever live in the frontend.
 * Errors follow the backend's RFC 9457 problem+json format.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''

export interface ProblemDetail {
  type?: string
  title?: string
  status?: number
  detail?: unknown
  request_id?: string | null
}

export class ApiError extends Error {
  readonly status: number
  readonly problem: ProblemDetail | null

  constructor(status: number, message: string, problem: ProblemDetail | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.problem = problem
  }
}

type QueryValue = string | number | boolean | null | undefined

/** Build a query string, skipping empty values. */
export function qs(params: Record<string, QueryValue>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const out = sp.toString()
  return out ? `?${out}` : ''
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/api/v1${path}`, {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'Impossibile contattare il server.')
  }

  if (!response.ok) {
    let problem: ProblemDetail | null = null
    try {
      problem = (await response.json()) as ProblemDetail
    } catch {
      problem = null
    }
    throw new ApiError(response.status, problem?.title ?? `Errore HTTP ${response.status}`, problem)
  }
  return (await response.json()) as T
}
