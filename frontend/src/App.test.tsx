import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { NAV_ITEMS } from './lib/navigation'
import { renderApp } from './test/render'

const healthy = {
  status: 'ok',
  version: '0.1.0',
  environment: 'test',
  database: 'ok',
  ai_provider: 'mock',
}

function mockFetch(impl: () => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(impl))
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App shell', () => {
  it('shows all eight sections in the sidebar', () => {
    mockFetch(() => jsonResponse(healthy))
    renderApp()
    const nav = screen.getByRole('navigation', { name: 'Navigazione principale' })
    for (const item of NAV_ITEMS) {
      expect(within(nav).getByRole('link', { name: item.label })).toBeInTheDocument()
    }
  })

  it.each(NAV_ITEMS)('renders the $label page', ({ path, label }) => {
    mockFetch(() => jsonResponse(healthy))
    renderApp(path)
    expect(screen.getByRole('heading', { level: 1, name: label })).toBeInTheDocument()
  })

  it('labels the simulation lab as simulation', () => {
    mockFetch(() => jsonResponse(healthy))
    renderApp('/simulazioni')
    expect(screen.getByRole('note')).toHaveTextContent('SIMULAZIONE')
  })

  it('renders a 404 page for unknown routes', () => {
    mockFetch(() => jsonResponse(healthy))
    renderApp('/non-esiste')
    expect(screen.getByText('Pagina non trovata')).toBeInTheDocument()
  })

  it('shows system status when the backend is healthy', async () => {
    mockFetch(() => jsonResponse(healthy))
    renderApp('/')
    expect(await screen.findByText('Connesso')).toBeInTheDocument()
    expect(screen.getByText('Simulato (offline)')).toBeInTheDocument()
    expect(screen.getByText('Sistema operativo')).toBeInTheDocument()
  })

  it('shows an error state with retry when the backend is unreachable', async () => {
    mockFetch(() => Promise.reject(new TypeError('network')))
    renderApp('/')
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Impossibile contattare il server.')
    expect(screen.getByText('Server non raggiungibile')).toBeInTheDocument()

    mockFetch(() => jsonResponse(healthy))
    await userEvent.click(within(alert).getByRole('button', { name: 'Riprova' }))
    expect(await screen.findByText('Connesso')).toBeInTheDocument()
  })

  it('warns when the database is unavailable', async () => {
    mockFetch(() => jsonResponse({ ...healthy, status: 'degraded', database: 'unavailable' }))
    renderApp('/')
    expect(await screen.findByText('Non disponibile')).toBeInTheDocument()
    expect(screen.getByText('Database non disponibile')).toBeInTheDocument()
  })
})
