import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockApi } from '../test/mockApi'
import { renderApp } from '../test/render'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AI Agents page', () => {
  it('starts an analysis and shows agent statuses, evidence and the master summary', async () => {
    const fetchMock = mockApi()
    renderApp('/agenti?partita=100')
    expect(await screen.findByText('Forma e contesto.')).toBeInTheDocument()
    expect(await screen.findByText('Simulato (offline, gratuito)')).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('button', { name: /Avvia analisi/ }))
    expect(await screen.findByText('Aquile ha 3 punti nelle ultime partite')).toBeInTheDocument()
    expect(screen.getByText('home.form5.points')).toBeInTheDocument()
    expect(screen.getByText('Saltato: dati insufficienti')).toBeInTheDocument()
    expect(screen.getByText('Sintesi di prova.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Apri il report completo/ })).toHaveAttribute('href', '/report/run-1')

    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ match_id: 100, force: false })
  })
})

describe('Reports', () => {
  it('lists reports', async () => {
    mockApi()
    renderApp('/report')
    expect(await screen.findByText('Sintesi di prova.')).toBeInTheDocument()
    expect(screen.getByText('Confidenza media')).toBeInTheDocument()
  })

  it('shows a full report with contradictions, missing data, sources and disclaimer', async () => {
    mockApi()
    renderApp('/report/run-1')
    expect(await screen.findByRole('heading', { level: 1, name: /Aquile – Borgo/ })).toBeInTheDocument()
    expect(screen.getByText('Classifica e simulazione divergono')).toBeInTheDocument()
    expect(screen.getByText('Valutazione: Campione ridotto')).toBeInTheDocument()
    expect(screen.getByText('Formazioni non disponibili dalla fonte')).toBeInTheDocument()
    expect(screen.getByText(/Nessun consiglio di scommessa/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Markdown/ })).toHaveAttribute('href', '/api/v1/analyses/run-1/report.md')
  })
})
