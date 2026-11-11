import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/hooks/useAuth'
import { VERIFY_REQUIRED_PATH } from '@/lib/navigation'

function SessionLoading() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background">
      <p className="text-sm text-muted-foreground">Loading…</p>
    </div>
  )
}

export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <SessionLoading />
  if (status === 'anonymous') {
    // The verify gate is not a destination, so don't remember it for after sign-in.
    const from = location.pathname === VERIFY_REQUIRED_PATH ? undefined : location.pathname
    return <Navigate to="/login" replace state={from ? { from } : undefined} />
  }
  return <Outlet />
}

export function RequireVerified() {
  const { user } = useAuth()

  if (user && !user.isVerified) return <Navigate to="/verify-required" replace />
  return <Outlet />
}
