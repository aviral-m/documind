import type { LucideIcon } from 'lucide-react'
import { Library, Plus, Settings } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'

import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

import { Logo } from './Logo'

interface AppSidebarProps {
  onNavigate?: () => void
}

export function AppSidebar({ onNavigate }: AppSidebarProps) {
  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <Link to="/" onClick={onNavigate} className="px-2 py-1">
        <Logo />
      </Link>

      <nav aria-label="Primary" className="flex flex-col gap-1">
        <SidebarLink to="/chat" label="New chat" icon={Plus} onNavigate={onNavigate} />
        <SidebarLink to="/documents" label="Library" icon={Library} onNavigate={onNavigate} />
      </nav>

      <section className="flex flex-col gap-2">
        <h2 className="px-3 text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Recent
        </h2>
        <p className="px-3 text-sm text-muted-foreground">No conversations yet.</p>
      </section>

      <div className="mt-auto flex flex-col gap-1">
        <Separator className="mb-2" />
        <SidebarLink to="/settings" label="Settings" icon={Settings} onNavigate={onNavigate} />
      </div>
    </div>
  )
}

interface SidebarLinkProps {
  to: string
  label: string
  icon: LucideIcon
  onNavigate?: () => void
}

function SidebarLink({ to, label, icon: Icon, onNavigate }: SidebarLinkProps) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
            : 'text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground',
        )
      }
    >
      <Icon className="size-4" aria-hidden />
      {label}
    </NavLink>
  )
}
