// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { IXPTable, sessoesRs } from './IXPTable'
import type { IXPIndexEntry } from '../../types/api'

const afi = { coleta: 'ok', total_routes: 10, unique_prefixes: 10, ixp_space: 0, ixp_space_units: 0, asn_direct_count: 0, asn_origin_count: 0, asn_stub_count: 0, br_asns_origin_count: 0, br_prefix_coverage_pct: 1, ixp_vs_fulltable_space_pct: 1 }
const ptt = (code: string, nome: string, extra: Partial<IXPIndexEntry>): IXPIndexEntry => ({ code, name: nome, uf: 'SP', status: 'ok', v4: afi, v6: afi, ...extra } as IXPIndexEntry)
const ixps = [
  ptt('sp', 'São Paulo', { cdns_curados: 50, route_servers: { v6: { up: 5693, down: 1743, sessoes: 7436, rs: 2 }, v4: { up: 5951, down: 1559, sessoes: 7510, rs: 2 }, rs_sem_vizinhos_atuais: 0 } }),
  ptt('ap', 'Macapá', { cdns_curados: 0, route_servers: null }),
  ptt('to', 'Palmas', { cdns_curados: 3, route_servers: { v6: { up: 36, down: 56, sessoes: 92, rs: 1 }, v4: null, rs_sem_vizinhos_atuais: 1 } }),
]
const interligacao = { route_servers: { fonte: 'Alice-LG', coletado_em: '2026-11-22T06:00:00+00:00', versao_alice: '6.1.0' }, cdns: { fonte: 'lista curada de CDNs', snapshot: '2026-11-22', cdns_na_lista: 59 } }
const montar = () => render(<MemoryRouter initialEntries={['/ixps?colunas=interligacao']}><IXPTable ixps={ixps} interligacao={interligacao} dataSnapshot="2026-11-22" /></MemoryRouter>)

describe('grupo "Interligação" da lista de PTTs (PT-24 / IXPS-E5.4)', () => {
  it('sessoesRs: up / down com separador de milhar e n/d (nunca zero) sem route server', () => {
    expect(sessoesRs({ up: 5693, down: 1743 })).toBe('5.693 / 1.743')
    expect(sessoesRs(null)).toBe('n/d')
    expect(sessoesRs(undefined)).toBe('n/d')
    expect(sessoesRs({ up: 0, down: 0 })).toBe('0 / 0')
  })

  it('mostra IPv6 antes de IPv4, CDNs e n/d no PTT sem route server; zero CDN é "0"', () => {
    montar()
    const cab = screen.getAllByRole('columnheader').map((c) => c.textContent ?? '')
    expect(cab.findIndex((t) => /route server IPv6/.test(t))).toBeLessThan(cab.findIndex((t) => /route server IPv4/.test(t)))
    const sp = screen.getAllByRole('row').find((l) => l.textContent?.includes('São Paulo'))!
    expect(sp.textContent).toContain('5.693 / 1.743')
    expect(sp.textContent).toContain('5.951 / 1.559')
    expect(within(sp).getByRole('link', { name: /50 CDNs da lista curada em São Paulo/ })).toHaveAttribute('href', expect.stringContaining('/cdns'))
    const ap = screen.getAllByRole('row').find((l) => l.textContent?.includes('Macapá'))!
    expect(ap.textContent).toContain('n/d')
    expect(ap.textContent).not.toMatch(/0 \/ 0/)
    const to = screen.getAllByRole('row').find((l) => l.textContent?.includes('Palmas'))!
    expect(to.textContent).toContain('36 / 56')
    expect(to.textContent).toContain('n/d')                                   // IPv4 sem route server com vizinhos atuais
  })

  it('traz fonte, selo e data das duas colunas e o aviso de leitura, sem juízo', () => {
    montar()
    expect(screen.getByText(/Fato · Alice-LG: sessões · ref\. 2026-11-22/)).toBeInTheDocument()
    expect(screen.getByText(/Fato · lista curada de CDNs \(59 CDNs na lista\): coluna de CDNs · ref\. 2026-11-22/)).toBeInTheDocument()
    expect(document.body.textContent).toMatch(/sessão down não indica a causa/)
    expect(document.body.textContent).toMatch(/sessões bilaterais não aparece/)
  })

  it('ordena por CDNs com n/d no fim nas duas direções e marca aria-sort', () => {
    montar()
    const linhas = () => Array.from(document.querySelectorAll('tbody tr')).map((l) => l.querySelector('a')?.textContent)
    const th = screen.getByRole('columnheader', { name: /CDNs da lista curada/ })
    fireEvent.click(within(th).getAllByRole('button')[0])
    expect(th).toHaveAttribute('aria-sort', 'ascending')
    expect(linhas()).toEqual(['Macapá', 'Palmas', 'São Paulo'])
    fireEvent.click(within(th).getAllByRole('button')[0])
    expect(linhas()).toEqual(['São Paulo', 'Palmas', 'Macapá'])
  })
})

describe('grupo "Sistemas autônomos": originadores e o subconjunto brasileiro (PT-24 / IXPS-E5.1)', () => {
  it('mostra "dos quais brasileiros" ao lado de Originadores, com o número do PTT', () => {
    const lista = [ptt('vix', 'Vitória', { asn_origin_union_count: 2292, br_asns_origin_union_count: 2100 })]
    render(<MemoryRouter initialEntries={['/ixps']}><IXPTable ixps={lista} /></MemoryRouter>)
    const cab = screen.getAllByRole('columnheader').map((c) => c.textContent ?? '')
    const i = cab.findIndex((t) => /^Originadores/.test(t))
    expect(i).toBeGreaterThan(-1)
    expect(cab[i + 1]).toMatch(/dos quais brasileiros/)
    const linha = screen.getAllByRole('row').find((l) => l.textContent?.includes('Vitória'))!
    expect(linha.textContent).toContain('2.292')
    expect(linha.textContent).toContain('2.100')
  })
})
