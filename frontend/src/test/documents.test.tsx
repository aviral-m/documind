import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { UploadCard } from '@/features/documents/UploadCard'
import { ApiError } from '@/lib/apiClient'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { documentService } from '@/services/documentService'
import type { DocumentSummary } from '@/types/document'

vi.mock('@/services/documentService', () => ({
  documentService: {
    list: vi.fn(),
    upload: vi.fn(),
    delete: vi.fn(),
    reindex: vi.fn(),
  },
}))

function doc(overrides: Partial<DocumentSummary>): DocumentSummary {
  return {
    id: 'doc-1',
    filename: 'report.pdf',
    status: 'completed',
    pageCount: 12,
    sizeBytes: 2048,
    errorMessage: null,
    indexStatus: null,
    indexError: null,
    chunkCount: null,
    createdAt: '2026-11-12T10:00:00Z',
    updatedAt: '2026-11-12T10:00:00Z',
    ...overrides,
  }
}

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('library page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows each document with its status, page count, and failure message', async () => {
    vi.mocked(documentService.list).mockResolvedValue([
      doc({ id: 'a', filename: 'report.pdf', status: 'completed', pageCount: 12 }),
      doc({
        id: 'b',
        filename: 'scan.pdf',
        status: 'failed',
        pageCount: null,
        errorMessage: "No extractable text. OCR isn't supported yet.",
      }),
    ])

    renderWithClient(<DocumentsPage />)

    expect(await screen.findByText('report.pdf')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByText('12 pages')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText("No extractable text. OCR isn't supported yet.")).toBeInTheDocument()
  })

  it('shows the indexing stage, chunk count, and index failure with a retry', async () => {
    vi.mocked(documentService.list).mockResolvedValue([
      doc({ id: 'a', filename: 'indexing.pdf', indexStatus: 'indexing' }),
      doc({ id: 'b', filename: 'ready.pdf', indexStatus: 'indexed', chunkCount: 42 }),
      doc({
        id: 'c',
        filename: 'broken.pdf',
        indexStatus: 'failed',
        indexError: 'Indexing failed. Please try again.',
      }),
    ])
    vi.mocked(documentService.reindex).mockResolvedValue(doc({ id: 'c', indexStatus: 'pending' }))

    renderWithClient(<DocumentsPage />)

    expect(await screen.findByText('Indexing…')).toBeInTheDocument()
    expect(screen.getByText('Ready to search · 42 chunks')).toBeInTheDocument()
    expect(screen.getByText('Indexing failed')).toBeInTheDocument()
    expect(screen.getByText('Indexing failed. Please try again.')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Try again' })).toHaveLength(1)

    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(documentService.reindex).toHaveBeenCalledWith('c')
  })

  it('shows the empty state when there are no documents', async () => {
    vi.mocked(documentService.list).mockResolvedValue([])

    renderWithClient(<DocumentsPage />)

    expect(await screen.findByText('Your library is empty')).toBeInTheDocument()
  })

  it('asks before deleting and removes the card on success', async () => {
    vi.mocked(documentService.list)
      .mockResolvedValueOnce([doc({ id: 'a', filename: 'report.pdf' })])
      .mockResolvedValue([])
    vi.mocked(documentService.delete).mockResolvedValue(undefined)
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderWithClient(<DocumentsPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Delete report.pdf' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('report.pdf'))
    expect(documentService.delete).toHaveBeenCalledWith('a')
    expect(await screen.findByText('Your library is empty')).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('does not delete when the user cancels the confirmation', async () => {
    vi.mocked(documentService.list).mockResolvedValue([doc({ id: 'a', filename: 'report.pdf' })])
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)

    renderWithClient(<DocumentsPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Delete report.pdf' }))

    expect(documentService.delete).not.toHaveBeenCalled()
    expect(screen.getByText('report.pdf')).toBeInTheDocument()
    confirm.mockRestore()
  })
})

describe('upload card', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function pickFile(container: HTMLElement, file: File) {
    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })
  }

  it('keeps Upload disabled until a PDF is chosen', async () => {
    const { container } = renderWithClient(<UploadCard />)
    const button = screen.getByRole('button', { name: 'Upload' })
    expect(button).toBeDisabled()

    pickFile(container, new File(['%PDF-1.4'], 'report.pdf', { type: 'application/pdf' }))

    expect(await screen.findByRole('button', { name: 'Upload' })).toBeEnabled()
  })

  it('uploads the chosen file', async () => {
    vi.mocked(documentService.upload).mockResolvedValue(doc({ status: 'pending' }))
    const { container } = renderWithClient(<UploadCard />)
    const file = new File(['%PDF-1.4'], 'report.pdf', { type: 'application/pdf' })

    pickFile(container, file)
    await userEvent.click(await screen.findByRole('button', { name: 'Upload' }))

    await waitFor(() => expect(documentService.upload).toHaveBeenCalledWith(file))
  })

  it('rejects a file over 10 MB without uploading it', async () => {
    const { container } = renderWithClient(<UploadCard />)
    const tooBig = new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'big.pdf', {
      type: 'application/pdf',
    })

    pickFile(container, tooBig)

    expect(await screen.findByText('PDF only, up to 10 MB.')).toBeInTheDocument()
    expect(screen.queryByText('big.pdf')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
    expect(documentService.upload).not.toHaveBeenCalled()
  })

  it('shows the server error on the card when the upload fails', async () => {
    vi.mocked(documentService.upload).mockRejectedValue(
      new ApiError('This PDF has more than 500 pages.', 422),
    )
    const { container } = renderWithClient(<UploadCard />)

    pickFile(container, new File(['%PDF-1.4'], 'big.pdf', { type: 'application/pdf' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Upload' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('This PDF has more than 500 pages.')
  })
})
