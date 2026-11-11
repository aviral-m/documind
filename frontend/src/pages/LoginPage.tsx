import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { AuthLayout } from '@/components/auth/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/hooks/useAuth'
import { API_BASE_URL, ApiError } from '@/lib/apiClient'
import { safeReturnPath } from '@/lib/navigation'

export function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const from = safeReturnPath((location.state as { from?: unknown } | null)?.from)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // The backend sends OAuth failures back here as ?error=...
  const shownError = error ?? searchParams.get('error')

  if (status === 'authenticated') return <Navigate to={from} replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Sign in" description="Welcome back to DocuMind.">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="email" className="text-sm font-medium">
            Email
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="password" className="text-sm font-medium">
            Password
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        {shownError ? (
          <p role="alert" className="text-sm text-destructive">
            {shownError}
          </p>
        ) : null}

        <Button type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <Separator className="flex-1" />
          or
          <Separator className="flex-1" />
        </div>

        <Button variant="outline" asChild>
          <a href={`${API_BASE_URL}/auth/oauth/google/authorize`}>Continue with Google</a>
        </Button>
        <Button variant="outline" asChild>
          <a href={`${API_BASE_URL}/auth/oauth/github/authorize`}>Continue with GitHub</a>
        </Button>

        <div className="flex flex-col gap-2 text-sm text-muted-foreground">
          <Link to="/forgot-password" className="hover:text-foreground">
            Forgot your password?
          </Link>
          <p>
            New to DocuMind?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </form>
    </AuthLayout>
  )
}
