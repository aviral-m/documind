import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, type InitialEntry } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from '@/App'
import { AuthProvider } from '@/features/auth/AuthProvider'
import { authService } from '@/services/authService'
import { healthService } from '@/services/healthService'
import type { User } from '@/types/auth'

vi.mock('@/services/authService', () => ({
  authService: {
    restoreSession: vi.fn(),
    login: vi.fn(),
    currentUser: vi.fn(),
    logout: vi.fn(),
  },
}))

vi.mock('@/services/healthService', () => ({
  healthService: {
    getDatabaseHealth: vi.fn(() => new Promise(() => {})),
  },
}))

const verifiedUser: User = {
  id: 'user-1',
  email: 'verified@example.com',
  name: null,
  isVerified: true,
}

function renderApp(entry: InitialEntry) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[entry]}>
          <App />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('sign-in redirect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(authService.restoreSession).mockResolvedValue(null)
    vi.mocked(authService.login).mockResolvedValue(undefined)
    vi.mocked(authService.currentUser).mockResolvedValue(verifiedUser)
    vi.mocked(healthService.getDatabaseHealth).mockImplementation(() => new Promise(() => {}))
  })

  it('sends a verified user to the dashboard, not the verify page, after signing in', async () => {
    const user = userEvent.setup()
    renderApp({ pathname: '/login', state: { from: '/verify-required' } })

    await user.type(screen.getByLabelText('Email'), 'verified@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Welcome to DocuMind' })).toBeInTheDocument()
  })

  it('returns a signed-out user to the protected page they asked for', async () => {
    const user = userEvent.setup()
    renderApp({ pathname: '/documents' })

    await user.type(await screen.findByLabelText('Email'), 'verified@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Library' })).toBeInTheDocument()
  })
})
