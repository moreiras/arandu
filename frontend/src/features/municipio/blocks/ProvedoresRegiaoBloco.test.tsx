// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProvedoresRegiaoBloco } from './RegiaoBlocos'
import type { MunicipioCtx } from '../contexto'
import type { Regiao, RegiaoProvedor } from '../../../types/api'

const prov = (asn: number, o: Partial<RegiaoProvedor> = {}): RegiaoProvedor => ({
  asn, nome: `Nome AS${asn}`, cnpj: null, vinculos: ['sici'], acessos_fixo: 0, acessos_movel: 0, prefixos_geo: 0, ptts_diretos: [], ptts_indiretos: [], ...o,
})
const PROVS = [
  ...[10, 11, 12, 13, 14].map((a) => prov(a, { cnpj: '02558157000162', nome: 'TELEFONICA BRASIL S.A', acessos_fixo: 300000, acessos_movel: 89385, ptts_diretos: a === 10 ? ['sp'] : [] })),
  prov(20, { cnpj: '40432544000147', nome: 'CLARO S.A.', acessos_fixo: 485130 }),
  prov(30, { nome: 'Empresário individual (AS30, CNPJ 12.***.***/0001-**)', acessos_fixo: 40 }),
  prov(40, { nome: 'Só IPs Ltda', vinculos: ['geo'], prefixos_geo: 6 }),
]
const regiao = { provedores: PROVS, provedores_total: PROVS.length, ibges: ['1', '2'], ptts_nomes: { sp: 'São Paulo' }, limites: 'lim',
  asns: { total: PROVS.length, por_vinculo: { sici: 7, sede: 0, geo: 1 } } } as unknown as Regiao
const montar = (conjunto?: MunicipioCtx['conjunto']) =>
  render(<MemoryRouter><ProvedoresRegiaoBloco dados={{ ibge: '1', proximos: [], carregandoPtts: false, regiao, conjunto }} {...({} as any)} /></MemoryRouter>)

describe('ProvedoresRegiaoBloco: uma linha por operadora', () => {
  it('a operadora com vários ASNs aparece uma vez, com os acessos uma vez e "+N" que abre a lista completa', () => {
    montar()
    const linhas = screen.getAllByTestId('regiao-linha')
    expect(linhas).toHaveLength(4)                                       // Telefônica (5 ASNs), Claro, EI e Só IPs
    const t = linhas.find((l) => l.textContent!.includes('TELEFONICA'))!
    expect(t.textContent).toContain('389.385')
    expect(t.textContent!.match(/389\.385/g)).toHaveLength(1)
    expect(within(t).getAllByRole('link', { name: /^AS\d+$/ })).toHaveLength(3)
    fireEvent.click(within(t).getByRole('button', { name: '+2' }))
    expect(within(t).getAllByRole('link', { name: /^AS\d+$/ })).toHaveLength(5)
    expect(within(t).getByRole('button', { name: 'recolher' })).toHaveAttribute('aria-expanded', 'true')
    expect(within(t).getByRole('link', { name: 'TELEFONICA BRASIL S.A' })).toHaveAttribute('href', '/operadora/02558157000162')
    expect(within(t).getByRole('link', { name: 'São Paulo' })).toHaveAttribute('href', '/ixp/sp')
  })

  it('empresário individual e ASN sem CNPJ: sem link para a operadora, linha própria', () => {
    montar()
    const ei = screen.getAllByTestId('regiao-linha').find((l) => l.textContent!.includes('Empresário individual'))!
    expect(within(ei).queryByRole('link', { name: /Empresário/ })).toBeNull()
    expect(within(ei).getByRole('link', { name: 'AS30' })).toBeInTheDocument()
    const so = screen.getAllByTestId('regiao-linha').find((l) => l.textContent!.includes('Só IPs'))!
    expect(within(so).queryByRole('link', { name: 'Só IPs Ltda' })).toBeNull()
    expect(so).toHaveTextContent('IPs')
  })

  it('o texto conta ASNs e linhas e não há travessão; cabeçalho com Operadora e ASNs', () => {
    montar()
    expect(screen.getByTestId('regiao-provedores')).toHaveTextContent('8 ASNs ligados aos municípios')
    expect(screen.getByTestId('regiao-provedores')).toHaveTextContent('4 linhas, sendo 2 operadoras identificadas pelo CNPJ e 2 ASNs sem CNPJ ligado')
    expect(screen.getAllByRole('columnheader').slice(0, 2).map((c) => c.textContent!.replace('↕', ''))).toEqual(['Operadora', 'ASNs'])
    expect(screen.queryByTestId('aviso-limite-regiao')).toBeNull()
  })

  it('avisa que a região foi limitada aos 50 municípios mais próximos', () => {
    montar({ n: 50, central: '1', cortado: true, dentroDoRaio: 202, raioKm: 245, raioEfetivoKm: 127.9 })
    const a = screen.getByTestId('aviso-limite-regiao')
    expect(a).toHaveTextContent('limitada aos 50 mais próximos')
    expect(a).toHaveTextContent('202 municípios')
  })
})
