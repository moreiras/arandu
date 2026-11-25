// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { fixtures, server } from '../test/server'
import { SITE } from '../lib/site'
import { UsoAceitavel } from './UsoAceitavel'

const montar = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><UsoAceitavel /></QueryClientProvider>)

describe('/uso-aceitavel', () => {
  it('lê o orçamento e o custo por chamada da rota de limites, sem número fixo no texto', async () => {
    server.use(http.get('*/api/v1/limites', () => HttpResponse.json({ ...fixtures.limites, sem_conta: { ...fixtures.limites.sem_conta, orcamento_diario_segundos: 1234, custo_por_chamada_segundos: 7 } })))
    montar()
    await waitFor(() => expect(screen.getByText(/\(hoje, 1234 s e 7 s\)/)).toBeTruthy())
    expect(screen.getByText(/são os publicados em \/dados e em \/api\/v1\/limites/)).toBeTruthy()
    expect(screen.queryByText(/600 s/)).toBeNull()
  })

  it('sem dado da rota omite o parêntese e não mostra número', async () => {
    server.use(http.get('*/api/v1/limites', () => new HttpResponse('boom', { status: 500 })))
    const { container } = montar()
    await waitFor(() => expect(screen.getByText(/são os publicados em/)).toBeTruthy())
    expect(container.textContent).not.toMatch(/hoje, /)
    expect(container.textContent).toMatch(/\/api\/v1\/limites; ao esgotá-lo/)
  })

  it('"fale conosco antes" traz o e-mail de contato em link mailto sublinhado', () => {
    montar()
    const a = screen.getByRole('link', { name: SITE.contato })
    expect(a.getAttribute('href')).toBe(`mailto:${SITE.contato}`)
    expect(a.className).toContain('underline')
    expect(a.parentElement!.textContent).toContain('fale conosco antes: ')
  })
})
