import type { ReactNode } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { API_BASE_URL } from '@/lib/apiClient'
import { BackendStatusPill } from '@/features/health/BackendStatusPill'

const preferences = [
  { label: 'Theme', value: 'Light (dark mode is not in Phase 1)' },
  { label: 'Account', value: 'Sign-in arrives in Phase 1.5' },
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
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Connection status and preferences.</p>
      </header>

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
