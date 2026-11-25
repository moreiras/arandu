// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { AppLayout } from './layout/AppLayout'
import { AuthProvider } from '../auth/AuthContext'
import { SnapshotHistoricoAviso } from './SnapshotHistoricoAviso'

function Local() { const l = useLocation(); return <p data-testid="local">{l.pathname + l.search}</p> }

describe('aviso de snapshot histórico (D3)', () => {
  it('explica o que é, oferece entrar e o botão leva ao snapshot atual sem a data', () => {
    render(
      <MemoryRouter initialEntries={['/municipio/4114351?aba=mercado&date=2026-11-08']}>
        <SnapshotHistoricoAviso data="2026-11-08" atuais={['2026-11-15', '2026-11-22']} />
        <Local />
      </MemoryRouter>,
    )
    const aviso = screen.getByTestId('snapshot-historico')
    expect(aviso.textContent).toMatch(/Snapshot histórico: 08\/11\/2026/)
    expect(aviso.textContent).toMatch(/15\/11\/2026 e 22\/11\/2026/)
    expect(aviso.textContent).toMatch(/Isto não é um erro/)
    expect(screen.getByRole('link', { name: /Entrar/ }).getAttribute('href')).toContain('/login?next=')
    fireEvent.click(screen.getByRole('button', { name: 'Ir para o snapshot atual' }))
    expect(screen.getByTestId('local').textContent).toBe('/municipio/4114351?aba=mercado')
  })

  it('janela anônima com ?date= antigo mostra a explicação no lugar da página, sem chamar a API da data e sem modal', async () => {
    const chamadas: string[] = []
    server.use(
      http.get('*/auth/me', () => HttpResponse.json({ authenticated: false, anon: { active_seconds: 0, limit_seconds: 600, limit_reached: false, heartbeat_interval_seconds: 15, inactivity_timeout_seconds: 45 } })),
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 2, latest: '2026-11-22', snapshots: ['2026-11-15', '2026-11-22'] })),
      http.get('*/api/v1/municipios/*', ({ request }) => { chamadas.push(request.url); return HttpResponse.json({}) }),
    )
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/municipio/4114351?date=2026-11-08']}>
          <AuthProvider>
            <Routes><Route element={<AppLayout />}><Route path="/municipio/:ibge" element={<p data-testid="pagina">página do município</p>} /></Route></Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('snapshot-historico')).toBeTruthy())
    expect(screen.queryByTestId('pagina')).toBeNull()
    expect(chamadas).toEqual([])
    expect(screen.queryByText('Entre para continuar')).toBeNull()
  })

  it('data entre as recentes abre a página normalmente', async () => {
    server.use(
      http.get('*/auth/me', () => HttpResponse.json({ authenticated: false, anon: { active_seconds: 0, limit_seconds: 600, limit_reached: false, heartbeat_interval_seconds: 15, inactivity_timeout_seconds: 45 } })),
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 2, latest: '2026-11-22', snapshots: ['2026-11-15', '2026-11-22'] })),
    )
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/municipio/4114351?date=2026-11-15']}>
          <AuthProvider>
            <Routes><Route element={<AppLayout />}><Route path="/municipio/:ibge" element={<p data-testid="pagina">página do município</p>} /></Route></Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('pagina')).toBeTruthy())
    expect(screen.queryByTestId('snapshot-historico')).toBeNull()
  })
})
