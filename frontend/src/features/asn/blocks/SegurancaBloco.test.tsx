// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SegurancaBloco } from './SegurancaBloco'
import type { SegurancaAsn } from '../../../types/api'

const fontes: SegurancaAsn['fontes'] = {
  rov: { fonte: 'APNIC Labs I-RoV', as_of: '2026-10-30', janela_dias: 7, copyright: '(c) APNIC' },
  dnssec: { fonte: 'APNIC Labs DNSSEC', as_of: '2026-10-29', janela_dias: 1, copyright: '(c) APNIC' },
  asrank: { fonte: 'CAIDA AS Rank', citacao: 'The CAIDA UCSD AS Rank' },
  bogons: { fonte: 'IANA e Team Cymru', lista_cymru_em: '2026-10-31' },
}
const base: SegurancaAsn = { snapshot_date: '2026-10-31', fontes, parametros: { min_amostras: 100 }, limites: 'ROV e DNSSEC são medições por amostragem.' }
const ctx = (seg: SegurancaAsn) => ({ dados: { seguranca: seg } } as any)

describe('bloco Segurança de roteamento do ASN', () => {
  it('mostra o percentual medido com a fonte, a janela e a amostra, e os bogons com a data da lista', () => {
    render(<SegurancaBloco {...ctx({ ...base, rov: { validates_pct: 0.26, amostras: 290351 }, dnssec: { validates_pct: 7.69, parcial_pct: 12.43, amostras: 64897 },
      asrank: { rank: 7887, cone: { asns: 2 }, grau: { cliente: 1, par: 29, provedor: 1 } }, n_prefixos_bogon: 3, prefixos_em_bogon: [{ prefixo: '100.80.0.0/18', lista: 'iana' }] })} />)
    expect(screen.getByText(/Validação RPKI medida \(APNIC, 7 dias até 2026-10-30\)/)).toBeTruthy()
    expect(screen.getByText('0,3%')).toBeTruthy()
    expect(screen.getByText(/290\.351 amostras/)).toBeTruthy()
    expect(screen.getByText(/Posição no AS Rank \(CAIDA, estimativa\)/)).toBeTruthy()
    expect(screen.getByText(/100\.80\.0\.0\/18/)).toBeTruthy()
    expect(screen.getByText(/medições por amostragem/)).toBeTruthy()
  })

  it('avisa quando a amostra é pequena e não inventa sinal que a fonte não trouxe', () => {
    render(<SegurancaBloco {...ctx({ ...base, rov: { validates_pct: 55, amostras: 40 } })} />)
    expect(screen.getByText(/poucas: valor instável/)).toBeTruthy()
    expect(screen.queryByText(/DNSSEC \(APNIC/)).toBeNull()
    expect(screen.queryByText(/bogon/)).toBeNull()
  })
})
