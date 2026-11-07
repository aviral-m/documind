import { useEffect, useState } from 'react'

import { useDatabaseHealth } from '@/hooks/useHealth'
import { ApiError } from '@/lib/apiClient'
import { cn } from '@/lib/utils'

const WAKING_THRESHOLD_MS = 4_000

interface StatusView {
  label: string
  detail?: string
  className: string
  dotClassName: string
}

type HealthQuery = ReturnType<typeof useDatabaseHealth>

function resolveStatus(query: HealthQuery, isSlow: boolean): StatusView {
  if (query.isSuccess) {
    return {
      label: 'Backend connected',
      detail: `Database responded in ${query.data.latency_ms} ms`,
      className: 'border-accent-foreground/15 bg-accent text-accent-foreground',
      dotClassName: 'bg-primary',
    }
  }

  if (query.isPending) {
    return isSlow
      ? {
          label: 'Database is waking up…',
          detail: 'Neon can take a few seconds to resume after being idle.',
          className: 'border-amber-300 bg-amber-50 text-amber-900',
          dotClassName: 'animate-pulse bg-amber-500',
        }
      : {
          label: 'Checking connection…',
          className: 'border-border bg-card text-muted-foreground',
          dotClassName: 'animate-pulse bg-muted-foreground',
        }
  }

  const error = query.error
  if (error instanceof ApiError && error.status === 503) {
    return {
      label: 'Database unavailable',
      detail: error.message,
      className: 'border-destructive/30 bg-destructive/10 text-destructive',
      dotClassName: 'bg-destructive',
    }
  }

  const offline = error instanceof ApiError && error.status === 0
  return {
    label: offline ? 'Backend offline' : 'Backend error',
    detail: error instanceof Error ? error.message : undefined,
    className: 'border-destructive/30 bg-destructive/10 text-destructive',
    dotClassName: 'bg-destructive',
  }
}

export function BackendStatusPill({ className }: { className?: string }) {
  const health = useDatabaseHealth()
  const [isSlow, setIsSlow] = useState(false)

  useEffect(() => {
    if (!health.isPending) return
    const timer = setTimeout(() => setIsSlow(true), WAKING_THRESHOLD_MS)
    return () => clearTimeout(timer)
  }, [health.isPending])

  const status = resolveStatus(health, isSlow)

  return (
    <span
      role="status"
      title={status.detail}
      className={cn(
        'inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium',
        status.className,
        className,
      )}
    >
      <span className={cn('size-2 rounded-full', status.dotClassName)} aria-hidden />
      {status.label}
    </span>
  )
}
