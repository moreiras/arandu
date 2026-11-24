// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** O número de um destaque tem de ser o total que a página de destino mostra (HOME-E3: 351 no destaque contra 2.147 no panorama). */
import { describe, expect, it } from 'vitest'
import { cartaoDe, consultaDoDestaque, DESTAQUES } from './regrasDestaques'

describe('destaque de divergências APNIC × Anatel (HOME-E3)', () => {
  const d = DESTAQUES.find((x) => x.id === 'divergencias')!

  it('usa a mesma rota e os mesmos parâmetros de regra do bloco do panorama de mercado, para onde leva', () => {
    const q = consultaDoDestaque(d)
    expect(q).toEqual({ tipo: 'get', caminho: '/api/v1/acessos/divergencias/scm', params: { limit: 1 } })
    // o panorama (`BandaLargaFixaSection`) chama a rota sem k_pf, k_pj nem min_razao: os padrões da API valem dos dois lados
    expect(Object.keys((q as { params: Record<string, unknown> }).params)).toEqual(['limit'])
    expect(d.to).toBe('/panorama/mercado')
    expect(cartaoDe(d).destino?.to).toBe('/panorama/mercado')
  })

  it('a unidade conta ASNs (a rota lista um ASN por CNPJ com um só ASN)', () => {
    expect(d.unidade).toBe('ASNs')
  })
})
