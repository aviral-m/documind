import { FileText, Inbox, ListChecks, Search } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState } from '@/components/EmptyState'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { DocumentCard } from '@/features/documents/DocumentCard'
import { UploadCard } from '@/features/documents/UploadCard'
import { BackendStatusPill } from '@/features/health/BackendStatusPill'
import { useDocuments } from '@/hooks/useDocuments'

const RECENT_DOCUMENT_LIMIT = 5

const quickStarts = [
  {
    title: 'Summarize a report',
    description: 'Get the key findings and conclusions from a long document.',
    icon: FileText,
  },
  {
    title: 'Find a specific clause',
    description: 'Locate passages and see the exact page they came from.',
    icon: Search,
  },
  {
    title: 'Build a checklist',
    description: 'Turn requirements or procedures into an actionable list.',
    icon: ListChecks,
  },
]

export function DashboardPage() {
  const { data: documents, isPending } = useDocuments()
  const recent = documents?.slice(0, RECENT_DOCUMENT_LIMIT) ?? []

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-semibold tracking-tight">Welcome to DocuMind</h1>
          <p className="text-muted-foreground">
            Upload documents and ask questions about them. Answers cite their sources.
          </p>
        </div>
        <BackendStatusPill />
      </header>

      <UploadCard />

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Recent documents</h2>
        {isPending ? (
          <Skeleton className="h-24" />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No documents yet"
            description="Documents you upload will appear here."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {recent.map((item) => (
              <DocumentCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Quick start</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {quickStarts.map((item) => (
            <Link key={item.title} to="/chat" className="group">
              <Card className="h-full transition-shadow group-hover:shadow-md">
                <CardHeader className="gap-3">
                  <item.icon className="size-5 text-primary" aria-hidden />
                  <CardTitle className="text-base">{item.title}</CardTitle>
                  <CardDescription>{item.description}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
