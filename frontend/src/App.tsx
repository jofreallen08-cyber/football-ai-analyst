import { Route, Routes } from 'react-router'

import { AppLayout } from './components/layout/AppLayout'
import { NAV_ITEMS } from './lib/navigation'
import { MatchCenter } from './pages/MatchCenter'
import { MatchDetail } from './pages/MatchDetail'
import { NotFound } from './pages/NotFound'
import { Overview } from './pages/Overview'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { PlayerAnalytics } from './pages/PlayerAnalytics'
import { TeamAnalytics } from './pages/TeamAnalytics'

const IMPLEMENTED = new Set(['/', '/partite', '/squadre', '/giocatori'])

/** Application routes. The router and query client are provided by the caller. */
export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Overview />} />
        <Route path="partite" element={<MatchCenter />} />
        <Route path="partite/:id" element={<MatchDetail />} />
        <Route path="squadre" element={<TeamAnalytics />} />
        <Route path="giocatori" element={<PlayerAnalytics />} />
        {NAV_ITEMS.filter((i) => !IMPLEMENTED.has(i.path)).map((item) => (
          <Route
            key={item.path}
            path={item.path.slice(1)}
            element={<PlaceholderPage item={item} simulation={item.path === '/simulazioni'} />}
          />
        ))}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
