import { Outlet } from 'react-router-dom'

import { AppSidebar } from './AppSidebar'
import { Logo } from './Logo'
import { MobileNav } from './MobileNav'

export function AppShell() {
  return (
    <div className="flex min-h-svh bg-background">
      <aside className="sticky top-0 hidden h-svh w-64 shrink-0 border-r border-sidebar-border bg-sidebar md:block">
        <AppSidebar />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background/90 px-4 py-3 backdrop-blur md:hidden">
          <MobileNav />
          <Logo />
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 md:px-10 md:py-10">
          <div className="mx-auto w-full max-w-5xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
