import { apiRequest } from '@/lib/apiClient'
import type { DocumentSummary } from '@/types/document'

interface DocumentDto {
  id: string
  filename: string
  status: DocumentSummary['status']
  page_count: number | null
  size_bytes: number
  error_message: string | null
  index_status: DocumentSummary['indexStatus']
  index_error: string | null
  chunk_count: number | null
  created_at: string
  updated_at: string
}

// Uploads can be large, so they get more time than the default request timeout.
const UPLOAD_TIMEOUT_MS = 120_000

function toDocument(dto: DocumentDto): DocumentSummary {
  return {
    id: dto.id,
    filename: dto.filename,
    status: dto.status,
    pageCount: dto.page_count,
    sizeBytes: dto.size_bytes,
    errorMessage: dto.error_message,
    indexStatus: dto.index_status,
    indexError: dto.index_error,
    chunkCount: dto.chunk_count,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  }
}

export const documentService = {
  async list(signal?: AbortSignal): Promise<DocumentSummary[]> {
    const documents = await apiRequest<DocumentDto[]>('/documents', {
      authenticated: true,
      signal,
    })
    return documents.map(toDocument)
  },

  async upload(file: File): Promise<DocumentSummary> {
    const form = new FormData()
    form.append('file', file)
    const document = await apiRequest<DocumentDto>('/documents', {
      method: 'POST',
      body: form,
      authenticated: true,
      timeoutMs: UPLOAD_TIMEOUT_MS,
    })
    return toDocument(document)
  },

  async reindex(id: string): Promise<DocumentSummary> {
    const document = await apiRequest<DocumentDto>(`/documents/${id}/reindex`, {
      method: 'POST',
      authenticated: true,
    })
    return toDocument(document)
  },

  delete(id: string): Promise<void> {
    return apiRequest<void>(`/documents/${id}`, { method: 'DELETE', authenticated: true })
  },
}
