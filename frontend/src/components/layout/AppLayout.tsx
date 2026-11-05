import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Outlet } from 'react-router'

import { HealthIndicator } from './HealthIndicator'
import { Logo } from './Logo'
import { Sidebar } from './Sidebar'

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="hidden border-r border-line bg-navy-900 lg:flex lg:flex-col print:hidden">
        <div className="border-b border-line px-5 py-4">
          <Logo />
        </div>
        <Sidebar />
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Chiudi menu"
            className="absolute inset-0 bg-black/60"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-line bg-navy-900">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <Logo />
              <button type="button" aria-label="Chiudi menu" onClick={() => setMenuOpen(false)}>
                <X className="size-5" />
              </button>
            </div>
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 print:hidden flex items-center justify-between gap-3 border-b border-line bg-navy-950/90 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Apri menu"
              className="rounded-md p-1.5 hover:bg-navy-800 lg:hidden"
              onClick={() => setMenuOpen(true)}
            >
              <Menu className="size-5" />
            </button>
            <div className="lg:hidden">
              <Logo />
            </div>
          </div>
          <HealthIndicator />
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>

        <footer className="border-t border-line px-4 py-3 text-xs text-ink-faint sm:px-6">
          Piattaforma di analisi calcistica a scopo educativo. Nessuna scommessa, quota o pronostico a
          pagamento. Le simulazioni sono scenari ipotetici, non risultati reali.
        </footer>
      </div>
    </div>
  )
}
