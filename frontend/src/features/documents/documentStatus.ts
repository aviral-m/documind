import type { DocumentStatus, DocumentSummary, IndexStatus } from '@/types/document'

const ACTIVE_STATUSES: readonly DocumentStatus[] = ['pending', 'processing']
const ACTIVE_INDEX_STATUSES: readonly IndexStatus[] = ['pending', 'indexing']

/** A document is still being processed and its status may change. */
export function isActiveStatus(status: DocumentStatus): boolean {
  return ACTIVE_STATUSES.includes(status)
}

/** Indexing has started or is queued. Only meaningful once extraction has completed. */
export function isActiveIndexStatus(status: IndexStatus | null): boolean {
  return status !== null && ACTIVE_INDEX_STATUSES.includes(status)
}

function isActiveDocument(document: DocumentSummary): boolean {
  return isActiveStatus(document.status) || isActiveIndexStatus(document.indexStatus)
}

export function hasActiveDocuments(documents: DocumentSummary[] | undefined): boolean {
  return documents?.some(isActiveDocument) ?? false
}

/** One combined stage label for the card, covering extraction and indexing. */
export function stageLabel(document: DocumentSummary): string {
  if (document.status === 'pending') return 'Pending'
  if (document.status === 'processing') return 'Processing'
  if (document.status === 'failed') return 'Failed'
  switch (document.indexStatus) {
    case 'pending':
    case 'indexing':
      return 'Indexing…'
    case 'indexed':
      return `Ready to search · ${document.chunkCount ?? 0} chunks`
    case 'failed':
      return 'Indexing failed'
    default:
      return 'Ready'
  }
}
