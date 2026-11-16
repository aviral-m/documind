import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { hasActiveDocuments } from '@/features/documents/documentStatus'
import { documentService } from '@/services/documentService'

export const documentsQueryKey = ['documents'] as const
const POLL_INTERVAL_MS = 3_000

export function useDocuments() {
  return useQuery({
    queryKey: documentsQueryKey,
    queryFn: ({ signal }) => documentService.list(signal),
    // Poll only while something is still pending or processing.
    refetchInterval: (query) => (hasActiveDocuments(query.state.data) ? POLL_INTERVAL_MS : false),
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => documentService.upload(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsQueryKey }),
  })
}

export function useReindexDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => documentService.reindex(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsQueryKey }),
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => documentService.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsQueryKey }),
  })
}
