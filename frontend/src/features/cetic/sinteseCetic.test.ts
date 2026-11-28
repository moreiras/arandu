// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese de Uso da Internet (PT-22): valores reais das planilhas (TIC Domicílios 2025, TIC Provedores 2024), margem, universo e edição na frase. */
import { describe, expect, it } from 'vitest'
import type { CeticLinha } from '../../types/api'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { TEMAS, celula, sinteseCetic, valorComMargem } from './sinteseCetic'

const L = (tabela: string, dimensao: string, recorte: string, item: string, resposta: string, proporcao: number | null, margem: number | null): CeticLinha =>
  ({ tabela, titulo_tabela: '', dimensao, recorte, item, resposta, proporcao, margem_proporcao: margem, total: null, margem_total: null })
const dom = { edicao: 2025, linhas: [
  L('A4', 'Total', 'Total', '', 'Sim', 86.3047, 0.798), L('A4', 'Total', 'Total', '', 'Não', 13.531, 0.78),
  L('A4', 'Classe social', 'A', '', 'Sim', 99.7797, 0.4753), L('A4', 'Classe social', 'DE', '', 'Sim', 73.4428, 1.3975),
  L('A5', 'Total', 'Total', 'Banda larga fixa', 'Total - Banda larga fixa', 76.36, 1.295),
] }
const prov = { edicao: 2024, linhas: [L('E1A', 'Total', 'Total', '', 'Sim', 34.4067, 2.4763), L('C1', 'Total', 'Total', '', 'Sim', 43.61, 0)] }

describe('sinteseCetic', () => {
  it('quatro frases com margem, universo, pesquisa e edição, e os mesmos valores das planilhas', () => {
    const f = sinteseCetic(dom, prov)
    expect(f.map((x) => x.id)).toEqual(['a4', 'a5', 'e1a', 'c1'])
    expect(f[0].texto).toBe('86,3% (±0,8) dos domicílios têm acesso à Internet; na classe social DE a proporção é 73,4% (±1,4) e na classe A, 99,8% (±0,5).')
    expect(f[1].texto).toContain('76,4% (±1,3) dos domicílios com acesso à Internet usam banda larga fixa')
    expect(f[1].texto).toContain('o universo são os domicílios com acesso à Internet')
    expect(f[2].texto).toBe('34,4% (±2,5) das empresas provedoras declaram participar do IX.br.')
    expect(f[0].fonte).toBe('TIC Domicílios 2025, tabela A4 (Cetic.br|NIC.br)')
    expect(f[2].fonte).toMatch(/TIC Provedores 2024, tabela E1A .*autodeclaração/)
    for (const x of f) { expect(x.selo).toBe('estimado'); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('margem registrada como zero na planilha não vira "±0,0" (C1: 43,6%)', () => {
    const c1 = sinteseCetic(dom, prov).find((x) => x.id === 'c1')!
    expect(c1.texto).toContain('43,6% (margem de erro registrada como zero na planilha do Cetic.br)')
    expect(c1.texto).not.toContain('±0,0')
  })

  it('precisão baixa é dita; margem ausente vira "margem não publicada"', () => {
    expect(valorComMargem(L('x', '', '', '', '', 2, 1.5))).toBe('2,0% (±1,5; precisão baixa)')
    expect(valorComMargem(L('x', '', '', '', '', 10, null))).toBe('10,0% (margem não publicada)')
  })

  it('edição sem a tabela: a frase some sem erro; sem nenhuma célula a síntese some; classe ausente só tira o complemento', () => {
    const semC1 = sinteseCetic(dom, { edicao: 2024, linhas: prov.linhas.filter((l) => l.tabela !== 'C1') })
    expect(semC1.map((x) => x.id)).toEqual(['a4', 'a5', 'e1a'])
    expect(sinteseCetic(undefined, undefined)).toEqual([])
    expect(sinteseCetic({ edicao: 2025, linhas: [] }, { edicao: 2024, linhas: [] })).toEqual([])
    const semClasse = sinteseCetic({ edicao: 2025, linhas: dom.linhas.filter((l) => l.dimensao === 'Total' || l.tabela === 'A5') }, undefined)
    expect(semClasse[0].texto).toBe('86,3% (±0,8) dos domicílios têm acesso à Internet.')
  })

  it('celula() exige igualdade nos cinco campos (A5 "Total - Banda larga fixa" não casa com "Conexão via rádio")', () => {
    const t = TEMAS.domicilios.find((x) => x.id === 'a5_banda_larga_fixa')!
    expect(celula([L('A5', 'Total', 'Total', 'Banda larga fixa', 'Conexão via rádio', 1.13, 0.3)], t)).toBeUndefined()
    expect(celula(dom.linhas, t)?.proporcao).toBe(76.36)
  })
})
