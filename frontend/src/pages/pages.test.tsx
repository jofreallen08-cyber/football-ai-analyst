import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockApi } from '../test/mockApi'
import { renderApp } from '../test/render'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Overview', () => {
  it('shows totals, recent and upcoming matches and sources', async () => {
    mockApi()
    renderApp('/')
    expect(await screen.findByText('Risultati recenti')).toBeInTheDocument()
    expect(screen.getAllByText('Aquile').length).toBeGreaterThan(0)
    expect(screen.getByText('2 – 0')).toBeInTheDocument()
    expect(screen.getByText('Risultati: openfootball')).toBeInTheDocument()
  })
})

describe('Match Center', () => {
  it('lists matches grouped by matchday with links to detail', async () => {
    mockApi()
    renderApp('/partite')
    expect(await screen.findByText('Giornata 1')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /Aquile.*2 – 0.*Borgo/ })
    expect(link).toHaveAttribute('href', '/partite/100')
    expect(screen.getByText(/2 partite · pagina 1 di 1/)).toBeInTheDocument()
  })

  it('labels synthetic seasons in the selector', async () => {
    mockApi()
    renderApp('/partite')
    expect(await screen.findByRole('option', { name: /Lega Dimostrativa 2026\/27 — sintetico/ })).toBeInTheDocument()
  })
})

describe('Match detail', () => {
  it('shows score, declares missing stats and attributes the source', async () => {
    mockApi()
    renderApp('/partite/100')
    expect(await screen.findByText('2 – 0')).toBeInTheDocument()
    expect(screen.getByText('Statistiche non disponibili')).toBeInTheDocument()
    expect(screen.getByText('Formazioni non disponibili')).toBeInTheDocument()
    expect(await screen.findByText('xG e statistiche di squadra non disponibili dalla fonte')).toBeInTheDocument()
    expect(screen.getByText('Risultati e calendari: openfootball')).toBeInTheDocument()
  })

  it('shows a not-found state for unknown matches', async () => {
    mockApi()
    renderApp('/partite/999')
    expect(await screen.findByText('Dati non disponibili')).toBeInTheDocument()
  })
})

describe('Team analytics', () => {
  it('defaults to the league leader and explains missing xG', async () => {
    mockApi()
    renderApp('/squadre')
    expect(await screen.findByRole('heading', { level: 2, name: 'Aquile' })).toBeInTheDocument()
    expect(screen.getByText('xG non disponibile')).toBeInTheDocument()
    expect(screen.getByText('Nota parità')).toBeInTheDocument()
  })
})

describe('Player analytics', () => {
  it('explains when a source has no player statistics', async () => {
    mockApi()
    renderApp('/giocatori')
    expect(await screen.findByText('Statistiche individuali non disponibili')).toBeInTheDocument()
  })
})
