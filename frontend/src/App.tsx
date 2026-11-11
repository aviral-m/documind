import { Route, Routes } from 'react-router-dom'

import { RequireAuth, RequireVerified } from '@/components/auth/RouteGuards'
import { AppShell } from '@/components/layout/AppShell'
import { ChatPage } from '@/pages/ChatPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { VerifyEmailPage } from '@/pages/VerifyEmailPage'
import { VerifyRequiredPage } from '@/pages/VerifyRequiredPage'

export function App() {
  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="verify-email" element={<VerifyEmailPage />} />
      <Route path="forgot-password" element={<ForgotPasswordPage />} />
      <Route path="reset-password" element={<ResetPasswordPage />} />

      <Route element={<RequireAuth />}>
        <Route path="verify-required" element={<VerifyRequiredPage />} />

        <Route element={<RequireVerified />}>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
