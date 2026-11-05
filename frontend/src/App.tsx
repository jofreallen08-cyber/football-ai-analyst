import { Route, Routes } from 'react-router'

import { AppLayout } from './components/layout/AppLayout'
import { NAV_ITEMS } from './lib/navigation'
import { NotFound } from './pages/NotFound'
import { Overview } from './pages/Overview'
import { PlaceholderPage } from './pages/PlaceholderPage'

/** Application routes. The router and query client are provided by the caller. */
export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Overview />} />
        {NAV_ITEMS.slice(1).map((item) => (
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
