import { describe, expect, it } from 'vitest'

import { hasActiveDocuments, isActiveStatus, stageLabel } from '@/features/documents/documentStatus'
import type { DocumentSummary } from '@/types/document'

function doc(
  status: DocumentSummary['status'],
  overrides: Partial<DocumentSummary> = {},
): DocumentSummary {
  return {
    id: status,
    filename: `${status}.pdf`,
    status,
    pageCount: null,
    sizeBytes: 1,
    errorMessage: null,
    indexStatus: null,
    indexError: null,
    chunkCount: null,
    createdAt: '2026-11-12T00:00:00Z',
    updatedAt: '2026-11-12T00:00:00Z',
    ...overrides,
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

  it('keeps polling while indexing is pending or running after extraction', () => {
    expect(hasActiveDocuments([doc('completed', { indexStatus: 'pending' })])).toBe(true)
    expect(hasActiveDocuments([doc('completed', { indexStatus: 'indexing' })])).toBe(true)
    expect(hasActiveDocuments([doc('completed', { indexStatus: 'indexed' })])).toBe(false)
    expect(hasActiveDocuments([doc('completed', { indexStatus: 'failed' })])).toBe(false)
  })
})

describe('stage label', () => {
  it('shows extraction stages before indexing starts', () => {
    expect(stageLabel(doc('pending'))).toBe('Pending')
    expect(stageLabel(doc('processing'))).toBe('Processing')
    expect(stageLabel(doc('failed'))).toBe('Failed')
  })

  it('shows the indexing stage once extraction has completed', () => {
    expect(stageLabel(doc('completed', { indexStatus: 'pending' }))).toBe('Indexing…')
    expect(stageLabel(doc('completed', { indexStatus: 'indexing' }))).toBe('Indexing…')
    expect(stageLabel(doc('completed', { indexStatus: 'indexed', chunkCount: 7 }))).toBe(
      'Ready to search · 7 chunks',
    )
    expect(stageLabel(doc('completed', { indexStatus: 'failed' }))).toBe('Indexing failed')
  })

  it('falls back to Ready for documents indexed before indexing existed', () => {
    expect(stageLabel(doc('completed'))).toBe('Ready')
  })
})
