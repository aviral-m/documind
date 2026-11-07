export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface DocumentSummary {
  id: string
  filename: string
  status: DocumentStatus
  pageCount: number | null
}
