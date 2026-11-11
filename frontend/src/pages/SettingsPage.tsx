import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BackendStatusPill } from '@/features/health/BackendStatusPill'
import { useAuth } from '@/hooks/useAuth'
import { API_BASE_URL } from '@/lib/apiClient'

const preferences = [
  { label: 'Theme', value: 'Light (dark mode is not in Phase 1)' },
  { label: 'Answer style', value: 'Available with chat in Phase 4' },
]

function SettingRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="font-medium">{label}</span>
      <div className="text-sm text-muted-foreground">{children}</div>
    </div>
  )
}

export function SettingsPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Account, connection status, and preferences.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>The account you're signed in with.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col divide-y">
          <SettingRow label="Name">{user?.name ?? 'Not set'}</SettingRow>
          <SettingRow label="Email">{user?.email}</SettingRow>
          <div className="flex justify-end py-3">
            <Button variant="outline" onClick={handleSignOut}>
              Sign out
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connection</CardTitle>
          <CardDescription>How this app reaches the backend.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col divide-y">
          <SettingRow label="API base URL">
            <code className="rounded bg-muted px-2 py-1 text-foreground">{API_BASE_URL}</code>
          </SettingRow>
          <SettingRow label="Backend status">
            <BackendStatusPill />
          </SettingRow>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
          <CardDescription>More options arrive in later phases.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col divide-y">
          {preferences.map((item) => (
            <SettingRow key={item.label} label={item.label}>
              {item.value}
            </SettingRow>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
