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

interface RequestOptions {
  signal?: AbortSignal
  timeoutMs?: number
}

export async function apiGet<T>(
  path: string,
  { signal, timeoutMs = DEFAULT_TIMEOUT_MS }: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const abortFromCaller = () => controller.abort()
  signal?.addEventListener('abort', abortFromCaller)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
    if (!response.ok) {
      throw new ApiError(await readErrorMessage(response), response.status)
    }
    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    const timedOut = controller.signal.aborted && !signal?.aborted
    throw new ApiError(timedOut ? 'The request timed out.' : 'Could not reach the server.', 0)
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abortFromCaller)
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null)
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  return response.statusText || `Request failed with status ${response.status}`
}
