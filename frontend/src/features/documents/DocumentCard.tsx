import { FileText, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useDeleteDocument } from '@/hooks/useDocuments'
import { ApiError } from '@/lib/apiClient'
import type { DocumentStatus, DocumentSummary } from '@/types/document'

const statusLabels: Record<DocumentStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Ready',
  failed: 'Failed',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function DocumentCard({ item }: { item: DocumentSummary }) {
  const remove = useDeleteDocument()

  function handleDelete() {
    if (!window.confirm(`Delete "${item.filename}"? This can't be undone.`)) return
    remove.mutate(item.id, {
      onSuccess: () => toast.success('Document deleted.'),
      onError: (error) =>
        toast.error(error instanceof ApiError ? error.message : 'Could not delete the document.'),
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
            <Badge variant="secondary">{statusLabels[item.status]}</Badge>
            {item.pageCount !== null ? <span>{item.pageCount} pages</span> : null}
            <span>Uploaded {formatDate(item.createdAt)}</span>
          </div>
          {item.status === 'failed' && item.errorMessage ? (
            <p className="text-sm text-destructive">{item.errorMessage}</p>
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
