// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { TelefoniaFixaSection } from './TelefoniaFixaSection'
import { TvPorAssinaturaSection } from './TvPorAssinaturaSection'

// recharts (ResponsiveContainer) mede o contêiner com ResizeObserver, que o jsdom não tem
beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} }) })

const stats = { snapshot_date: '2026-11-22', total: 2100, unique_cnpjs: 1685, geolocated: 2000, matched_asns: 400, cnpjs_with_asn: 412, uf_breakdown: [] }

const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{el}</QueryClientProvider>,
)

describe('licença × ASN nas seções de STFC e SeAC', () => {
  for (const [nome, Secao, servico] of [['STFC', TelefoniaFixaSection, 'acessos de STFC'], ['SeAC', TvPorAssinaturaSection, 'assinantes de SeAC']] as const) {
    it(`${nome}: descreve o cruzamento por CNPJ, sem prometer acessos nem dizer que a operadora está fora do BGP`, async () => {
      server.use(http.get('*/api/v1/outorgas/stats', () => HttpResponse.json(stats)))
      montar(<Secao />)
      expect(await screen.findByText('Parcela com ASN')).toBeTruthy()
      const texto = document.body.textContent ?? ''
      expect(texto).toContain('1.685 CNPJs')
      expect(texto).toContain(`Esta página não traz ${servico}`)
      expect(texto).toContain('O cruzamento é por CNPJ')
      expect(texto).not.toMatch(/ausentes do BGP|autonomiza|autônomos|viraram AS|~1\.[47]00/)
    })
  }
})
