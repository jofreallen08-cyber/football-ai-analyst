import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { NAV_ITEMS } from './lib/navigation'
import { health, mockApi } from './test/mockApi'
import { renderApp } from './test/render'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App shell', () => {
  it('shows all eight sections in the sidebar', () => {
    mockApi()
    renderApp()
    const nav = screen.getByRole('navigation', { name: 'Navigazione principale' })
    for (const item of NAV_ITEMS) {
      expect(within(nav).getByRole('link', { name: item.label })).toBeInTheDocument()
    }
  })

  it.each(NAV_ITEMS)('renders the $label page', ({ path, label }) => {
    mockApi()
    renderApp(path)
    expect(screen.getByRole('heading', { level: 1, name: label })).toBeInTheDocument()
  })

  it('labels the simulation lab as simulation', () => {
    mockApi()
    renderApp('/simulazioni')
    expect(screen.getByRole('note')).toHaveTextContent('SIMULAZIONE')
  })

  it('renders a 404 page for unknown routes', () => {
    mockApi()
    renderApp('/non-esiste')
    expect(screen.getByText('Pagina non trovata')).toBeInTheDocument()
  })

  it('shows an error state with retry when the backend is unreachable', async () => {
    mockApi({ '/overview': new TypeError('network'), '/health': new TypeError('network') })
    renderApp('/')
    const alerts = await screen.findAllByRole('alert')
    expect(alerts[0]).toHaveTextContent('Impossibile contattare il server.')
    expect(await screen.findByText('Server non raggiungibile')).toBeInTheDocument()

    mockApi()
    await userEvent.click(within(alerts[0]!).getByRole('button', { name: 'Riprova' }))
    expect(await screen.findByText('Risultati recenti')).toBeInTheDocument()
  })

  it('warns when the database is unavailable', async () => {
    mockApi({ '/health': { ...health, status: 'degraded', database: 'unavailable' } })
    renderApp('/')
    expect(await screen.findByText('Database non disponibile')).toBeInTheDocument()
  })
})
