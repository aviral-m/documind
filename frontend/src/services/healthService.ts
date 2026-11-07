import { apiGet } from '@/lib/apiClient'
import type { DatabaseHealthResponse, LivenessResponse } from '@/types/health'

// Neon can take several seconds to wake from idle, so the database check gets a longer timeout.
const DATABASE_HEALTH_TIMEOUT_MS = 20_000

export const healthService = {
  getLiveness: (signal?: AbortSignal) => apiGet<LivenessResponse>('/health', { signal }),
  getDatabaseHealth: (signal?: AbortSignal) =>
    apiGet<DatabaseHealthResponse>('/health/db', {
      signal,
      timeoutMs: DATABASE_HEALTH_TIMEOUT_MS,
    }),
}
