import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { authService } from '@/services/authService'
import type { RegisterInput, User } from '@/types/auth'

import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  useEffect(() => {
    let cancelled = false
    authService
      .restoreSession()
      .then((restored) => {
        if (cancelled) return
        setUser(restored)
        setStatus(restored ? 'authenticated' : 'anonymous')
      })
      .catch(() => {
        if (!cancelled) setStatus('anonymous')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await authService.login(email, password)
    setUser(await authService.currentUser())
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (input: RegisterInput) => {
    await authService.register(input)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      setUser(null)
      setStatus('anonymous')
      queryClient.clear()
    }
  }, [queryClient])

  const refreshUser = useCallback(async () => {
    const current = await authService.currentUser()
    setUser(current)
    return current
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, register, logout, refreshUser }),
    [status, user, login, register, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
