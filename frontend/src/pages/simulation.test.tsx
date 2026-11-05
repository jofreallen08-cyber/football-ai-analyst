import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockApi } from '../test/mockApi'
import { renderApp } from '../test/render'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Simulation Lab', () => {
  it('runs a simulation for a match and shows labelled, reproducible results', async () => {
    const fetchMock = mockApi()
    renderApp('/simulazioni?partita=100')
    expect(screen.getByRole('note')).toHaveTextContent('SIMULAZIONE')
    expect(await screen.findByText('Mario Bomber')).toBeInTheDocument()
    expect(screen.getByText(/segnalato indisponibile/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Usa indisponibili segnalati' }))
    await userEvent.click(screen.getByRole('button', { name: /Esegui simulazione/ }))

    expect(await screen.findByText('Scenario base')).toBeInTheDocument()
    expect(screen.getByText('Riproducibilità')).toBeInTheDocument()
    expect(screen.getByText('poisson-v1')).toBeInTheDocument()
    expect(screen.getAllByText(/SIMULAZIONE/).length).toBeGreaterThan(1)

    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(post).toBeDefined()
    const body = JSON.parse(String(post?.[1]?.body))
    expect(body).toMatchObject({ match_id: 100, unavailable_player_ids: [7], seed: 2026, n_iterations: 20000 })
  })

  it('shows the API error when a simulation cannot run', async () => {
    mockApi({ 'POST /simulations': undefined })
    renderApp('/simulazioni?partita=100')
    await screen.findByText('Mario Bomber')
    await userEvent.click(screen.getByRole('button', { name: /Esegui simulazione/ }))
    expect(await screen.findByText('Simulazione non eseguita')).toBeInTheDocument()
  })
})
