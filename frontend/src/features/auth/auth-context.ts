import { createContext } from 'react'

import type { RegisterInput, User } from '@/types/auth'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<User>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
