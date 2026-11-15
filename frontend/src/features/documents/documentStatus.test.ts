import { describe, expect, it } from 'vitest'

import { hasActiveDocuments, isActiveStatus } from '@/features/documents/documentStatus'
import type { DocumentSummary } from '@/types/document'

function doc(status: DocumentSummary['status']): DocumentSummary {
  return {
    id: status,
    filename: `${status}.pdf`,
    status,
    pageCount: null,
    sizeBytes: 1,
    errorMessage: null,
    createdAt: '2026-11-12T00:00:00Z',
    updatedAt: '2026-11-12T00:00:00Z',
  }
}

describe('document status polling', () => {
  it('keeps polling only for pending and processing', () => {
    expect(isActiveStatus('pending')).toBe(true)
    expect(isActiveStatus('processing')).toBe(true)
    expect(isActiveStatus('completed')).toBe(false)
    expect(isActiveStatus('failed')).toBe(false)
  })

  it('polls when any document is still active', () => {
    expect(hasActiveDocuments([doc('completed'), doc('processing')])).toBe(true)
  })

  it('stops polling when every document has finished', () => {
    expect(hasActiveDocuments([doc('completed'), doc('failed')])).toBe(false)
  })

  it('does not poll before any data has loaded', () => {
    expect(hasActiveDocuments(undefined)).toBe(false)
    expect(hasActiveDocuments([])).toBe(false)
  })
})
