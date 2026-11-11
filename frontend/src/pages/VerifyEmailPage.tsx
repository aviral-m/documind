import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { AuthLayout } from '@/components/auth/AuthLayout'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { ApiError } from '@/lib/apiClient'
import { authService } from '@/services/authService'

type VerifyState = 'pending' | 'success' | 'error'

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { status, refreshUser } = useAuth()

  const [state, setState] = useState<VerifyState>(token ? 'pending' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is missing its verification code.')
  // Verification links are single-use, so StrictMode's double effect must not send the request twice.
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) return
    started.current = true
    authService
      .verifyEmail(token)
      .then(async () => {
        setState('success')
        if (status === 'authenticated') await refreshUser()
      })
      .catch((err: unknown) => {
        setState('error')
        setMessage(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
      })
  }, [token, status, refreshUser])

  if (state === 'pending') {
    return (
      <AuthLayout title="Verifying your email">
        <p className="text-sm text-muted-foreground">One moment…</p>
      </AuthLayout>
    )
  }

  if (state === 'success') {
    return (
      <AuthLayout title="Email verified" description="Your account is ready.">
        <Button asChild>
          <Link to={status === 'authenticated' ? '/' : '/login'}>
            {status === 'authenticated' ? 'Continue to DocuMind' : 'Sign in'}
          </Link>
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Couldn't verify your email" description={message}>
      <Button asChild variant="outline">
        <Link to={status === 'authenticated' ? '/verify-required' : '/login'}>
          {status === 'authenticated' ? 'Request a new link' : 'Back to sign in'}
        </Link>
      </Button>
    </AuthLayout>
  )
}
