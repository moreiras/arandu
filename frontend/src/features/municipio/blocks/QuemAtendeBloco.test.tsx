// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QuemAtendeBloco } from './QuemAtendeBloco'
import type { Regiao, SiciOperador } from '../../../types/api'

const op = (cnpj: string, empresa: string, acessos: number, asns: number[] = []): SiciOperador => ({ cnpj, empresa, acessos, share: 0, asns })
const prov = (asn: number, diretos: string[], indiretos: string[] = [], nome = `Nome AS${asn}`) =>
  ({ asn, nome, vinculos: ['sici' as const], acessos_fixo: 0, acessos_movel: 0, prefixos_geo: 0, ptts_diretos: diretos, ptts_indiretos: indiretos })
const regiao = (provedores: ReturnType<typeof prov>[]) => ({ provedores, provedores_total: provedores.length, ptts_nomes: { bel: 'Belém', sp: 'São Paulo' } }) as unknown as Regiao
const montar = (operadores: SiciOperador[], reg: Regiao | null) =>
  render(<MemoryRouter><QuemAtendeBloco dados={{ ibge: '1', proximos: [], carregandoPtts: false, regiao: reg, fixo: { operadores } as never }} {...({} as any)} /></MemoryRouter>)

describe('QuemAtendeBloco (PT-26, município 5.2)', () => {
  const ops = [
    op('11111111000111', 'COELHO TECNOLOGIA', 1239, [264525]),
    op('22222222000122', 'CLICK IP', 6076),
    op('33333333000133', 'Nenhum Informado', 365, [265052]),
    op('44444444000144', 'Empresário individual (AS65000, CNPJ **.***.678/0001-**)', 300, [65000]),
    op('55555555000155', 'Pequena A', 5, [10]),
    op('66666666000166', 'Pequena B', 3),
  ]
  const reg = regiao([prov(264525, ['bel', 'sp'], ['pr']), prov(265052, [], ['ba'], 'RN TELECOM LTDA'), prov(65000, []), prov(10, [])])

  it('mostra os três indicadores com selo inferido, as linhas em ordem e "Demais (2)"', () => {
    montar(ops, reg)
    const total = 1239 + 6076 + 365 + 300 + 5 + 3
    expect(screen.getByTestId('qa-asn')).toHaveTextContent(`${(((1239 + 365 + 300 + 5) / total) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
    expect(screen.getByTestId('qa-direta')).toHaveTextContent(`${((1239 / total) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
    expect(screen.getByTestId('qa-indireta')).toHaveTextContent(`${((365 / total) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
    for (const id of ['qa-asn', 'qa-direta', 'qa-indireta']) expect(within(screen.getByTestId(id)).getByText('Inferido', { exact: false })).toBeInTheDocument()
    const linhas = screen.getAllByTestId('qa-linha').map((l) => l.textContent!)
    expect(linhas).toHaveLength(4)
    expect(linhas[0]).toMatch(/CLICK IP/)
    expect(linhas[0]).toMatch(/sem ASN/)
    expect(linhas[0]).toMatch(/n\/d/)
    expect(linhas[1]).toMatch(/COELHO/)
    expect(linhas[1]).toMatch(/AS264525/)
    expect(linhas[1]).toMatch(/Belém, São Paulo/)
    expect(screen.getByTestId('qa-demais')).toHaveTextContent('Demais (2)')
    expect(screen.getByTestId('qa-demais')).toHaveTextContent('8')
  })

  it('"Nenhum Informado" mostra o nome do ASN com a nota', () => {
    montar(ops, reg)
    const linha = screen.getAllByTestId('qa-linha').find((l) => l.textContent!.includes('RN TELECOM'))!
    expect(linha.textContent).not.toMatch(/Nenhum Informado/)
    expect(document.body.textContent).toMatch(/\(\*\) O SICI informa "Nenhum Informado"/)
  })

  it('empresário individual sai como chega (mascarado), sem link para a operadora', () => {
    montar(ops, reg)
    const linha = screen.getAllByTestId('qa-linha').find((l) => l.textContent!.includes('Empresário individual'))!
    expect(linha.textContent).toMatch(/CNPJ \*\*\.\*\*\*\.678\/0001-\*\*/)
    expect(within(linha).queryByRole('link', { name: /Empresário individual/ })).toBeNull()
    expect(linha.textContent).not.toMatch(/44\.444\.444/)
    expect(within(linha).getByRole('link', { name: 'AS65000' })).toBeInTheDocument()
  })

  it('o botão mostra as operadoras menores individualmente e a soma segue fechando', () => {
    montar(ops, reg)
    fireEvent.click(screen.getByRole('button', { name: /Mostrar as 2 operadoras menores/ }))
    expect(screen.queryByTestId('qa-demais')).toBeNull()
    expect(screen.getAllByTestId('qa-linha')).toHaveLength(6)
  })

  it('tabela com legenda e cabeçalhos de coluna; rótulos descritivos, sem juízo', () => {
    montar(ops, reg)
    expect(screen.getAllByRole('columnheader').map((c) => c.textContent)).toEqual(['Operadora', 'Fixo local', 'ASN', 'Sessão direta em PTT (IX.br)', 'Só indireto, via'])
    expect(document.querySelector('caption')).not.toBeNull()
    expect(document.body.textContent).toMatch(/não mede qualidade de rede/)
    expect(document.body.textContent).not.toMatch(/—|–/)
  })
})
