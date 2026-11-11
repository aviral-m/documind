import { type FormEvent, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { AuthLayout } from '@/components/auth/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/useAuth'
import { ApiError } from '@/lib/apiClient'

const MIN_PASSWORD_LENGTH = 8

export function RegisterPage() {
  const { register, status } = useAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  if (status === 'authenticated') return <Navigate to="/" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register({ email, password, name: name.trim() || undefined })
      setSubmittedEmail(email)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submittedEmail) {
    return (
      <AuthLayout title="Check your email" description="One more step before you can start.">
        <div className="flex flex-col gap-4 text-sm">
          <p>
            We sent a verification link to <span className="font-medium">{submittedEmail}</span>.
            Open it to verify your account.
          </p>
          <Button asChild variant="outline">
            <Link to="/login">Back to sign in</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Upload documents and ask questions about them."
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="name" className="text-sm font-medium">
            Name <span className="font-normal text-muted-foreground">(optional)</span>
          </label>
          <Input
            id="name"
            autoComplete="name"
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
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

        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}

        <Button type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </Button>

        <p className="text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
