import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '@/features/auth/AuthProvider'
import { LoginPage } from '@/pages/LoginPage'
import { authService } from '@/services/authService'

vi.mock('@/services/authService', () => ({
  authService: {
    restoreSession: vi.fn(),
    login: vi.fn(),
    currentUser: vi.fn(),
    logout: vi.fn(),
  },
}))

function renderLogin(url: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[url]}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('login page sign-in options', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(authService.restoreSession).mockResolvedValue(null)
  })

  it('links the Google and GitHub buttons to the backend sign-in routes', async () => {
    renderLogin('/login')

    expect(await screen.findByRole('link', { name: 'Continue with Google' })).toHaveAttribute(
      'href',
      '/api/v1/auth/oauth/google/authorize',
    )
    expect(screen.getByRole('link', { name: 'Continue with GitHub' })).toHaveAttribute(
      'href',
      '/api/v1/auth/oauth/github/authorize',
    )
  })

  it('shows the message the backend sends back after a failed provider sign-in', async () => {
    renderLogin(`/login?error=${encodeURIComponent("Couldn't sign in with Google. Try again.")}`)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Couldn't sign in with Google. Try again.",
    )
  })
})
