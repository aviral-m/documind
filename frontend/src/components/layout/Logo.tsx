import { FileText } from 'lucide-react'

export function Logo() {
  return (
    <span className="flex items-center gap-2">
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <FileText className="size-4" aria-hidden />
      </span>
      <span className="text-base font-semibold tracking-tight">DocuMind</span>
    </span>
  )
}
