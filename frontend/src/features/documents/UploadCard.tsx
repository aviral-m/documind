import { FileText, UploadCloud, X } from 'lucide-react'
import { useRef, useState, type DragEvent, type KeyboardEvent } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useUploadDocument } from '@/hooks/useDocuments'
import { cn } from '@/lib/utils'

const MAX_FILE_SIZE_MB = 10
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadCard() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const upload = useUploadDocument()

  function selectFile(candidate: File | undefined) {
    if (!candidate) return
    if (!isPdf(candidate)) {
      toast.error('Only PDF files can be uploaded.')
      return
    }
    if (candidate.size > MAX_FILE_SIZE_BYTES) {
      toast.error(`Files must be ${MAX_FILE_SIZE_MB} MB or smaller.`)
      return
    }
    upload.reset()
    setFile(candidate)
  }

  function clearFile() {
    upload.reset()
    setFile(null)
  }

  function startUpload() {
    if (!file) return
    upload.mutate(file, {
      onSuccess: () => {
        toast.success('Upload complete. Processing will start shortly.')
        setFile(null)
      },
    })
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files[0])
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      inputRef.current?.click()
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a document</CardTitle>
        <CardDescription>PDF only, up to {MAX_FILE_SIZE_MB} MB.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={handleKeyDown}
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
            isDragging
              ? 'border-primary bg-accent'
              : 'border-border bg-muted/40 hover:border-primary/60',
          )}
        >
          <UploadCloud className="size-8 text-primary" aria-hidden />
          <p className="font-medium">Drag a PDF here, or click to browse</p>
          <p className="text-sm text-muted-foreground">Your file stays private to your account.</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(event) => {
            selectFile(event.target.files?.[0])
            event.target.value = ''
          }}
        />

        {file ? (
          <div className="flex items-center justify-between gap-3 rounded-lg border bg-card px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText className="size-5 shrink-0 text-primary" aria-hidden />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Remove file"
              disabled={upload.isPending}
              onClick={clearFile}
            >
              <X />
            </Button>
          </div>
        ) : null}

        {upload.isError ? (
          <p role="alert" className="text-sm text-destructive">
            {upload.error instanceof Error ? upload.error.message : 'Upload failed. Try again.'}
          </p>
        ) : null}

        <div className="flex justify-end">
          <Button disabled={!file || upload.isPending} onClick={startUpload}>
            {upload.isPending ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
