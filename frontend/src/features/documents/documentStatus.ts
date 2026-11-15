import type { DocumentStatus, DocumentSummary } from '@/types/document'

const ACTIVE_STATUSES: readonly DocumentStatus[] = ['pending', 'processing']

/** A document is still being processed and its status may change. */
export function isActiveStatus(status: DocumentStatus): boolean {
  return ACTIVE_STATUSES.includes(status)
}

export function hasActiveDocuments(documents: DocumentSummary[] | undefined): boolean {
  return documents?.some((document) => isActiveStatus(document.status)) ?? false
}
