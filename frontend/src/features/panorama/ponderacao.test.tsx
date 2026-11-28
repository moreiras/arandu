// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** PT-15 / TRANSV-E6: a média ponderada de ROV e DNSSEC nunca aparece sozinha; a mediana e as faixas vêm ao lado. */
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import { ComoLerNumerosPais, KpisSegurancaPais, referenciaMedicao } from './IndicadoresBrasil'
import { GrupoFontes } from '../../components/ui'

// os valores medidos de `/brasil/indicadores` em 2026-11-22 (analise-obint, TRANSV-E6)
const ROV = { asns: 4144, mediana_pct: 0.14, media_ponderada_pct: 6.38, faixas: { ate_10: 3648, de_10_a_90: 307, acima_de_90: 189 }, fonte: { fonte: 'APNIC Labs', as_of: '2026-11-15' } }
const DNSSEC = { asns: 942, mediana_pct: 95.94, media_ponderada_pct: 39.35, faixas: { ate_10: 74, de_10_a_90: 211, acima_de_90: 657 }, fonte: { fonte: 'APNIC Labs', as_of: '2026-11-15' } }

const kpi = (rotulo: string) => screen.getAllByTestId('kpi').find((k) => k.getAttribute('data-kpi-rotulo') === rotulo)!

describe('média ponderada com mediana e faixas ao lado (PT-15 / TRANSV-E6)', () => {
  beforeEach(() => {
    useAppStore.setState({ activeDate: '2026-11-22', latestSnapshot: '2026-11-22' })
    server.use(http.get('*/api/v1/brasil/indicadores', () => HttpResponse.json({ snapshot_date: '2026-11-22',
      ipv6: { usuarios: 1000, usuarios_ipv6: 605, pct_usuarios_ipv6: 60.5, asns_com_estimativa: 10, asns_com_ipv6: 7, fonte: 'APNIC', nota: '' },
      rov: ROV, dnssec: DNSSEC, prontidao: { agregado: { asns: 10, classes: {}, asns_com_indice: 9, media_ponderada_usuarios: 7.1, mediana: 3, medicoes: {}, cobertura_pilares: {} }, pilares: {} } })))
  })
  const montar = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><KpisSegurancaPais /></MemoryRouter></QueryClientProvider>)

  it('ROV: 6,38 ponderada por amostras, com mediana 0,14, 4.144 ASes medidos e as faixas 3.648 / 307 / 189', async () => {
    montar()
    await screen.findByText('6,38%')
    const k = kpi('Filtragem de rotas inválidas (ROV, média ponderada por amostras)')
    expect(k).toHaveTextContent('6,38%')
    expect(k).toHaveTextContent('mediana das redes: 0,14% (4.144 ASes medidos)')
    expect(k).toHaveTextContent('3.648 até 10%, 307 de 10% a 90%, 189 acima de 90%')
  })

  it('DNSSEC: 39,35 ponderada, mediana 95,94 e faixas 74 / 211 / 657', async () => {
    montar()
    await screen.findByText('39,35%')
    const k = kpi('Validação de DNSSEC (média ponderada por amostras)')
    expect(k).toHaveTextContent('mediana das redes: 95,94% (942 ASes medidos)')
    expect(k).toHaveTextContent('74 até 10%, 211 de 10% a 90%, 657 acima de 90%')
  })

  it('a prontidão se diz ponderada por usuários, e não por amostras: as duas ponderações têm rótulos distintos', async () => {
    montar()
    await screen.findByText('6,38%')
    expect(kpi('Prontidão em segurança de roteamento (média ponderada por usuários)')).toBeInTheDocument()
  })

  it('sem mediana publicada, não inventa referência', () => {
    expect(referenciaMedicao({ asns: 3, media_ponderada_pct: 5 })).toBeUndefined()
    expect(referenciaMedicao(null)).toBeUndefined()
  })

  it('o "Como ler" separa as três medidas de IPv6 e diz que a mediana trata cada rede igual', () => {
    render(<GrupoFontes comoLer={<ComoLerNumerosPais />}><span /></GrupoFontes>)
    const t = screen.getByTestId('como-ler-texto').textContent!
    expect(t).toMatch(/conta as redes com prefixo IPv6 na tabela global/)
    expect(t).toMatch(/conta os usuários estimados/)
    expect(t).toMatch(/não indica anúncio nem uso/)
    expect(t).toMatch(/mediana trata todas as redes do mesmo modo/)
    expect(t).toMatch(/os usuários estimados de cada rede/)
  })
})
