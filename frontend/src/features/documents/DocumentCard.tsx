import { FileText } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { DocumentStatus, DocumentSummary } from '@/types/document'

const statusLabels: Record<DocumentStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Ready',
  failed: 'Failed',
}

export function DocumentCard({ item }: { item: DocumentSummary }) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3">
        <FileText className="size-5 shrink-0 text-primary" aria-hidden />
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <p className="truncate font-medium">{item.filename}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{statusLabels[item.status]}</Badge>
            {item.pageCount !== null ? <span>{item.pageCount} pages</span> : null}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
