// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

vi.mock('maplibre-gl', () => {
  class Ctl { }
  class Map { addControl() {} on() {} once() {} isStyleLoaded() { return false } remove() {} resize() {} getSource() { return undefined } }
  return { Popup: Ctl, addProtocol: () => {}, setWorkerUrl: () => {}, NavigationControl: Ctl, ScaleControl: Ctl, AttributionControl: Ctl, Marker: Ctl, Map }
})

import { server } from '../../test/server'
import { FacilityPage } from '../../pages/FacilityPage'
import type { FacilityDetalhe } from '../../types/api'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

const det: FacilityDetalhe = {
  snapshot_date: '2026-11-22', coletado_em: '2026-11-22T06:00:00Z', fonte: { nome: 'PeeringDB', url: 'https://www.peeringdb.com' }, limites: 'Cadastro autodeclarado no PeeringDB.',
  id: 5140, nome: 'FTZ01', org_nome: 'Ascenty', cidade: 'Fortaleza', uf: 'CE', pais: 'BR', escopo: 'brasil', n_redes: 5, n_redes_br: 4, redes_declaradas: 5,
  ixps: [{ ix_id: 1, code: 'ce', nome: 'IX.br Fortaleza', tipo: 'ixbr' }, { ix_id: 2, code: 'netix', nome: 'NetIX', tipo: 'externo' }], carriers: [], campus: null,
  redes: [
    { asn: 64496, nome: 'REDE UM', is_br: true, no_vinculo_desde: '2019-05-25T00:00:00Z', usuarios_apnic: 1131927, ipv6: true, situacao: { ce: 'sessao_rs' } },
    { asn: 64497, nome: 'REDE DOIS', is_br: true, usuarios_apnic: null, ipv6: true, situacao: { ce: 'membro_sem_sessao_rs' } },
    { asn: 64498, nome: 'REDE TRES', is_br: true, usuarios_apnic: 10, ipv6: false, situacao: { ce: 'so_origina' } },
    { asn: 64499, nome: 'REDE QUATRO', is_br: true, usuarios_apnic: null, ipv6: null, situacao: { ce: 'sem_presenca' } },
    { asn: 15169, nome: 'Estrangeira', is_br: false },
  ],
  redes_total: 5, redes_nota: 'Vínculos de redes a instalações do Brasil, como cadastrados no PeeringDB.',
  redes_perfil: {
    resumo: [{ ixp: 'ce', nome: 'IX.br Fortaleza', coleta: { v6: 'ok', v4: 'ok' }, redes_do_brasil: 4, sessao_rs: 1, membro_sem_sessao_rs: 1, so_origina: 1, sem_presenca: 1, sem_coleta: 0 }],
    ptts_sem_dado_de_sessao: [{ ix_id: 2, code: 'netix', nome: 'NetIX', tipo: 'externo' }],
    situacoes: { sessao_rs: 'a', membro_sem_sessao_rs: 'b', so_origina: 'c', sem_presenca: 'd', sem_coleta: 'e' }, inferidas: ['so_origina'],
    nota: 'Conta, entre as redes que declaram estar nesta instalação no PeeringDB, quantas têm sessão no route server do PTT. A rede pode participar do PTT por outra instalação.',
  },
}
const chamadas: URLSearchParams[] = []
function montar() {
  server.use(http.get('*/api/v1/facilities/:id', ({ request }) => { chamadas.push(new URL(request.url).searchParams); return HttpResponse.json(det) }))
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/instalacao/5140']}><Routes><Route path="/instalacao/:id" element={<FacilityPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}

describe('redes do prédio com a situação no PTT local (PT-24 / INST-E5.1)', () => {
  it('pede o perfil das redes e mostra a contagem por situação, com PTT externo "sem dado de sessão"', async () => {
    montar()
    const bloco = await screen.findByTestId('interligacao-predio')
    expect(chamadas[0].get('include')).toBe('redes_perfil')
    expect(bloco.textContent).toMatch(/IX\.br Fortaleza \(CE\): 4 redes do Brasil deste prédio · 1 sessão com o route server · 1 no cadastro, sem sessão com o route server · 1 só origina prefixos \(inferido\) · 1 sem presença observada/)
    expect(bloco.textContent).toMatch(/NetIX: sem dado de sessão neste site/)
    expect(bloco.textContent).toMatch(/Como ler/)
    expect(bloco.textContent).toMatch(/Fato · .* · ref\. 2026-11-22/)
    expect(bloco.textContent).toMatch(/Inferido · .*só origina/)
    expect(bloco.textContent).toMatch(/Estimado · APNIC Labs/)
    expect(bloco.textContent).not.toMatch(/ausente|oportunidade|fora do PTT/i)
  })

  it('a tabela mostra usuários (sem estimativa quando nulo), IPv6 e a situação em texto; só rede do Brasil tem situação', async () => {
    montar()
    await screen.findByTestId('interligacao-predio')
    const tabela = screen.getByRole('table')
    expect(within(tabela).getByText(/Redes que declaram estar nesta instalação/)).toBeInTheDocument()                    // caption
    const linha = (asn: string) => within(tabela).getByText(asn).closest('tr')!
    expect(linha('AS64496').textContent).toContain('1.131.927')
    expect(linha('AS64496').textContent).toContain('sessão com o route server')
    expect(linha('AS64497').textContent).toContain('sem estimativa')
    expect(linha('AS64497').textContent).toContain('no cadastro, sem sessão com o route server')
    expect(linha('AS15169').textContent).toContain('fora do Brasil: sem dado')
    const cab = within(tabela).getAllByRole('columnheader')
    expect(cab.every((c) => c.getAttribute('scope') === 'col')).toBe(true)
    expect(within(tabela).getByRole('columnheader', { name: /Usuários/ })).not.toHaveAttribute('aria-sort')              // usuários não ordena a tabela (política editorial)
  })

  it('o filtro de situação no PTT mostra só as redes com aquela situação', async () => {
    montar()
    await screen.findByTestId('interligacao-predio')
    fireEvent.change(screen.getByRole('combobox', { name: /Situação no PTT/ }), { target: { value: 'so_origina' } })
    const corpo = screen.getByRole('table').querySelector('tbody')!
    expect(corpo.textContent).toContain('AS64498')
    expect(corpo.textContent).not.toContain('AS64496')
    expect(screen.getByText('Redes (1)')).toBeInTheDocument()
  })
})
