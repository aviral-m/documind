import { type FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { AuthLayout } from '@/components/auth/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/apiClient'
import { authService } from '@/services/authService'

const MIN_PASSWORD_LENGTH = 8

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!token) {
    return (
      <AuthLayout title="Reset link missing" description="Open the link from your email again.">
        <Button asChild variant="outline">
          <Link to="/forgot-password">Request a new link</Link>
        </Button>
      </AuthLayout>
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (password !== confirmPassword) {
      setError('The passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await authService.resetPassword(token!, password)
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <AuthLayout title="Password updated" description="You can sign in with your new password.">
        <Button asChild>
          <Link to="/login">Sign in</Link>
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Choose a new password">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="password" className="text-sm font-medium">
            New password
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            At least {MIN_PASSWORD_LENGTH} characters.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="confirm-password" className="text-sm font-medium">
            Confirm new password
          </label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </div>

        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}

        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save new password'}
        </Button>
      </form>
    </AuthLayout>
  )
}
