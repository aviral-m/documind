import { FileText, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { stageLabel } from '@/features/documents/documentStatus'
import { useDeleteDocument, useReindexDocument } from '@/hooks/useDocuments'
import { ApiError } from '@/lib/apiClient'
import type { DocumentSummary } from '@/types/document'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function DocumentCard({ item }: { item: DocumentSummary }) {
  const remove = useDeleteDocument()
  const reindex = useReindexDocument()

  function handleDelete() {
    if (!window.confirm(`Delete "${item.filename}"? This can't be undone.`)) return
    remove.mutate(item.id, {
      onSuccess: () => toast.success('Document deleted.'),
      onError: (error) =>
        toast.error(error instanceof ApiError ? error.message : 'Could not delete the document.'),
    })
  }

  function handleRetryIndexing() {
    reindex.mutate(item.id, {
      onError: (error) =>
        toast.error(error instanceof ApiError ? error.message : 'Could not start indexing.'),
    })
  }

  return (
    <Card>
      <CardContent className="flex items-start gap-3">
        <FileText className="size-5 shrink-0 text-primary" aria-hidden />
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <p className="truncate font-medium" title={item.filename}>
            {item.filename}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{stageLabel(item)}</Badge>
            {item.pageCount !== null ? <span>{item.pageCount} pages</span> : null}
            <span>Uploaded {formatDate(item.createdAt)}</span>
          </div>
          {item.status === 'failed' && item.errorMessage ? (
            <p className="text-sm text-destructive">{item.errorMessage}</p>
          ) : null}
          {item.indexStatus === 'failed' && item.indexError ? (
            <p className="text-sm text-destructive">{item.indexError}</p>
          ) : null}
          {item.indexStatus === 'failed' ? (
            <div>
              <Button
                variant="outline"
                size="sm"
                disabled={reindex.isPending}
                onClick={handleRetryIndexing}
              >
                Try again
              </Button>
            </div>
          ) : null}
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Delete ${item.filename}`}
          disabled={remove.isPending}
          onClick={handleDelete}
        >
          <Trash2 />
        </Button>
      </CardContent>
    </Card>
  )
}
