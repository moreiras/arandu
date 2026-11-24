// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { IXPTable } from '../../components/tables/IXPTable'
import { coletaDaFamilia, isIXPAfiFull, type IXPAfi, type IXPIndexEntry } from '../../types/api'
import { rotuloColeta } from './CabecalhoPtt'
import { getIndexAfi } from './ui'

const afi = (rotas: number, pct: number | null, coleta?: 'ok' | 'vazia') => ({
  ...(coleta ? { coleta } : {}), total_routes: rotas, unique_prefixes: rotas, ixp_space: 0, ixp_space_units: 0, asn_direct_count: 0,
  asn_origin_count: 0, asn_stub_count: 0, br_asns_origin_count: 0, br_prefix_coverage_pct: pct, ixp_vs_fulltable_space_pct: pct,
})
const ptt = (code: string, v6: ReturnType<typeof afi>): IXPIndexEntry => ({ code, name: code.toUpperCase(), uf: 'BA', status: 'ok', v4: afi(5000, 50, 'ok'), v6 })

describe('coleta por família do PTT (IXP-E1, IXPS-E4)', () => {
  it('tabela vazia do looking glass não é dado completo nem 0%, inclusive em resposta sem o campo `coleta`', () => {
    expect(coletaDaFamilia(afi(0, null, 'vazia'))).toBe('vazia')
    expect(coletaDaFamilia(afi(0, 0))).toBe('vazia')                      // índice publicado antes do campo
    expect(coletaDaFamilia({ status: 'missing' })).toBe('missing')
    expect(isIXPAfiFull(afi(0, null, 'vazia') as unknown as IXPAfi)).toBe(false)
    expect(isIXPAfiFull(afi(10, 3, 'ok') as unknown as IXPAfi)).toBe(true)
    expect(getIndexAfi(afi(0, 0))).toBeNull()
  })

  it('o cabeçalho não diz "ok": diz quantas rotas, ou que a coleta veio vazia', () => {
    expect(rotuloColeta('IPv6', 'ok', 241338)).toBe('IPv6: 241.338 rotas coletadas')
    expect(rotuloColeta('IPv6', 'vazia', null)).toBe('IPv6: coleta feita, zero rotas no looking glass')
    expect(rotuloColeta('IPv4', 'missing', null)).toBe('IPv4: sem dados neste snapshot')
  })

  it('na lista de PTTs a família vazia mostra "zero rotas", sem porcentagem, e fica no fim da ordenação nas duas direções', () => {
    const ixps = [ptt('fec', afi(0, null, 'vazia')), ptt('ba', afi(900, 20, 'ok')), ptt('ce', afi(241338, 60, 'ok'))]
    render(<MemoryRouter initialEntries={['/ixps?colunas=ipv6']}><IXPTable ixps={ixps} /></MemoryRouter>)
    const linhas = () => screen.getAllByRole('row').slice(1).map((l) => within(l).getAllByRole('link')[0].textContent)
    const fec = screen.getAllByRole('row').find((l) => l.textContent?.includes('FEC'))!
    expect(within(fec).getByText('zero rotas')).toBeInTheDocument()
    expect(fec.textContent).not.toMatch(/0[,.]0%/)
    const cobertura = screen.getByRole('button', { name: /Cobertura Registro\.br/ })
    fireEvent.click(cobertura)
    expect(linhas()).toEqual(['BA', 'CE', 'FEC'])
    fireEvent.click(cobertura)
    expect(linhas()).toEqual(['CE', 'BA', 'FEC'])
  })
})
