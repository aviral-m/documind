import { useQuery } from '@tanstack/react-query'

import { healthService } from '@/services/healthService'

export const databaseHealthQueryKey = ['health', 'database'] as const

export function useDatabaseHealth() {
  return useQuery({
    queryKey: databaseHealthQueryKey,
    queryFn: ({ signal }) => healthService.getDatabaseHealth(signal),
    retry: false,
    refetchInterval: 30_000,
  })
}
