export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type IndexStatus = 'pending' | 'indexing' | 'indexed' | 'failed'

export interface DocumentSummary {
  id: string
  filename: string
  status: DocumentStatus
  pageCount: number | null
  sizeBytes: number
  errorMessage: string | null
  indexStatus: IndexStatus | null
  indexError: string | null
  chunkCount: number | null
  createdAt: string
  updatedAt: string
}
