import { MessageSquare } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export function ChatPage() {
  return (
    <div className="flex min-h-[70svh] flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">New chat</h1>
        <p className="text-muted-foreground">
          Ask questions about your documents. Answers will cite their sources.
        </p>
      </header>

      <div className="flex flex-1 flex-col justify-center">
        <EmptyState
          icon={MessageSquare}
          title="Chat arrives in Phase 4"
          description="Grounded answers with citations will appear here."
        />
      </div>

      <div className="flex flex-col gap-2 rounded-xl border bg-card p-3">
        <Textarea
          disabled
          placeholder="Ask a question about your documents…"
          className="min-h-20 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
        />
        <div className="flex justify-end">
          <Button disabled>Send</Button>
        </div>
      </div>
    </div>
  )
}
