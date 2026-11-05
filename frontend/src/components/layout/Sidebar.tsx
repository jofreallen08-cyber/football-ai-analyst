import { NavLink } from 'react-router'

import { NAV_ITEMS } from '../../lib/navigation'

interface SidebarProps {
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <nav aria-label="Navigazione principale" className="flex h-full flex-col gap-1 p-3">
      {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
        <NavLink
          key={path}
          to={path}
          end={path === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? 'bg-navy-700 text-ink shadow-inner ring-1 ring-line'
                : 'text-ink-muted hover:bg-navy-800 hover:text-ink'
            }`
          }
        >
          <Icon className="size-4.5 shrink-0" aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
