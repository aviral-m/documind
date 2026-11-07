import { Library } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { DocumentCard } from '@/features/documents/DocumentCard'
import type { DocumentSummary } from '@/types/document'

export function DocumentsPage() {
  // Phase 2 replaces this with documents loaded from the API.
  const documents: DocumentSummary[] = []

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">Library</h1>
        <p className="text-muted-foreground">Your documents and their processing status.</p>
      </header>

      {documents.length === 0 ? (
        <EmptyState
          icon={Library}
          title="Your library is empty"
          description="Uploaded documents will appear here once uploads are available in Phase 2."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {documents.map((item) => (
            <DocumentCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
