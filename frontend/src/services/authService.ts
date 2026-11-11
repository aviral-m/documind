import { apiRequest, refreshSession, setAccessToken } from '@/lib/apiClient'
import type { RegisterInput, User } from '@/types/auth'

interface UserDto {
  id: string
  email: string
  name: string | null
  avatar_url: string | null
  is_verified: boolean
}

interface TokenDto {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

interface MessageDto {
  message: string
}

function toUser(dto: UserDto): User {
  return { id: dto.id, email: dto.email, name: dto.name, isVerified: dto.is_verified }
}

export const authService = {
  register: (input: RegisterInput) =>
    apiRequest<MessageDto>('/auth/register', { method: 'POST', body: input }),

  async login(email: string, password: string): Promise<void> {
    const token = await apiRequest<TokenDto>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setAccessToken(token.access_token)
  },

  async currentUser(): Promise<User> {
    return toUser(await apiRequest<UserDto>('/auth/me', { authenticated: true }))
  },

  /** Silently restores a session from the refresh cookie, if one exists. */
  async restoreSession(): Promise<User | null> {
    const refreshed = await refreshSession()
    if (!refreshed) return null
    return authService.currentUser()
  },

  async logout(): Promise<void> {
    try {
      await apiRequest<void>('/auth/logout', { method: 'POST' })
    } finally {
      setAccessToken(null)
    }
  },

  verifyEmail: (token: string) =>
    apiRequest<MessageDto>('/auth/verify-email', { method: 'POST', body: { token } }),

  resendVerification: (email: string) =>
    apiRequest<MessageDto>('/auth/resend-verification', { method: 'POST', body: { email } }),

  forgotPassword: (email: string) =>
    apiRequest<MessageDto>('/auth/forgot-password', { method: 'POST', body: { email } }),

  resetPassword: (token: string, password: string) =>
    apiRequest<MessageDto>('/auth/reset-password', {
      method: 'POST',
      body: { token, password },
    }),
}
