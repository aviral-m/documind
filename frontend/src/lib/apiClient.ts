export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const DEFAULT_TIMEOUT_MS = 10_000

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE'
  /** Objects are sent as JSON. FormData is sent as-is so the browser sets the multipart boundary. */
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
  /** Sends the in-memory access token and refreshes once on 401. */
  authenticated?: boolean
}

// The access token is held in memory only, never in localStorage or sessionStorage.
let accessToken: string | null = null
let pendingRefresh: Promise<boolean> | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

/** Exchanges the httpOnly refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<boolean> {
  if (!pendingRefresh) {
    pendingRefresh = fetchNewAccessToken().finally(() => {
      pendingRefresh = null
    })
  }
  return pendingRefresh
}

async function fetchNewAccessToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) {
      accessToken = null
      return false
    }
    const body = (await response.json()) as { access_token: string }
    accessToken = body.access_token
    return true
  } catch {
    accessToken = null
    return false
  }
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const {
    method = 'GET',
    body,
    signal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    authenticated = false,
  } = options
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const abortFromCaller = () => controller.abort()
  signal?.addEventListener('abort', abortFromCaller)

  const isFormData = body instanceof FormData
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined && !isFormData) headers['Content-Type'] = 'application/json'
  if (authenticated && accessToken) headers.Authorization = `Bearer ${accessToken}`

  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body:
        body === undefined || isFormData ? (body as BodyInit | undefined) : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch {
    const timedOut = controller.signal.aborted && !signal?.aborted
    throw new ApiError(timedOut ? 'The request timed out.' : 'Could not reach the server.', 0)
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abortFromCaller)
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options)
  if (response.status === 401 && options.authenticated && (await refreshSession())) {
    response = await send(path, options)
  }
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function apiGet<T>(
  path: string,
  { signal, timeoutMs }: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<T> {
  return apiRequest<T>(path, { signal, timeoutMs })
}

async function readErrorMessage(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null)
  if (body && typeof body === 'object' && 'detail' in body) {
    const { detail } = body
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first: unknown = detail[0]
      if (first && typeof first === 'object' && 'msg' in first && typeof first.msg === 'string') {
        return first.msg
      }
    }
  }
  return response.statusText || `Request failed with status ${response.status}`
}
