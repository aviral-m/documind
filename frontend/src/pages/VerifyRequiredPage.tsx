import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { AuthLayout } from '@/components/auth/AuthLayout'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { ApiError } from '@/lib/apiClient'
import { authService } from '@/services/authService'

export function VerifyRequiredPage() {
  const { user, refreshUser, logout } = useAuth()
  const navigate = useNavigate()
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user?.isVerified) return <Navigate to="/" replace />

  async function handleResend() {
    if (!user) return
    setError(null)
    setBusy(true)
    try {
      await authService.resendVerification(user.email)
      setMessage('If that account needs verifying, a new link is on its way.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setBusy(false)
    }
  }

  async function handleCheckAgain() {
    setError(null)
    setBusy(true)
    try {
      const current = await refreshUser()
      if (current.isVerified) {
        navigate('/', { replace: true })
      } else {
        setError("This account isn't verified yet. Open the link in your email first.")
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setBusy(false)
    }
  }

  async function handleSignOut() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <AuthLayout
      title="Verify your email"
      description={`Open the verification link we sent to ${user?.email ?? 'your inbox'} to use DocuMind.`}
    >
      <div className="flex flex-col gap-3">
        <Button onClick={handleCheckAgain} disabled={busy}>
          I've verified my email
        </Button>
        <Button variant="outline" onClick={handleResend} disabled={busy}>
          Send a new link
        </Button>
        <Button variant="ghost" onClick={handleSignOut} disabled={busy}>
          Sign out
        </Button>

        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>
    </AuthLayout>
  )
}
