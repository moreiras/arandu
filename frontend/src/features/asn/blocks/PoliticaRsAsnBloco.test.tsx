// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { PoliticaRsAsnBloco } from './PoliticaRsAsnBloco'
import type { PoliticaAsn } from '../../../types/api'

const pol: PoliticaAsn = {
  snapshot_date: '2026-11-05', coletado_nivel2: '2026-11-06T22:00:00Z', coletado_nivel3: '2026-11-06T22:10:00Z', fonte: 'https://lg.ix.br (Alice-LG)', versao_alice: '6.1.0',
  parametros: { amostra_prefixos: 5, min_rotas_perfil: 10, fracao_seletivo: 0.1, fracao_restritivo: 0.5, alvos_restritivo: 50 },
  limites: 'Declaração por communities e decisão do route server; o perfil é inferido.', asn: 64496, nome: 'REDE EXEMPLO',
  evidencia_rs: { rotas_rejeitadas: 40, rpki_invalido: 25, bogon: 10, ptts: 1 },
  ixps: {
    df: {
      politica: { rotas: 100, sessoes: 1, afis: ['v4'], perfil: 'seletivo', perfil_criterio: "ação 'nao_exportar_para' em 30% das rotas (limite 10%)", perfil_inferido: true,
        acoes: { nao_exportar_para: { alvos: [{ alvo: 64510, rotulo: 'No export to AS64510', rotas: 30, fracao: 0.3, forma: 'equivalente_padrao' }, { alvo: 64511, rotulo: 'No export to AS64511', rotas: 1, fracao: 0.004, forma: 'dicionario' }], alvos_total: 1, rotas_max: 30, fracao_max: 0.3 } },
        blackhole_rotas: 2, rpki: { valid: 90, unknown: 10, not_checked: 0, invalid: 0 }, communities_distintas: 7, coletado_de: '2026-11-06', coletado_ate: '2026-11-06', contagem: 'exata' },
      rejeicoes: { rotas: 40, sessoes: 1, afis: ['v4'], sem_motivo: 0, coletado_de: '2026-11-06', coletado_ate: '2026-11-06', contagem: 'exata',
        motivos: [{ codigo: '26162:300:0', rotulo: 'Invalid on RPKI', classe: 'rejeicao', rotas: 25, amostra: [{ p: '198.18.0.0/32', o: 64496 }, { p: '198.18.0.1/32', o: 64496 }] }] },
    },
  },
}
const montar = (p: PoliticaAsn) => render(<MemoryRouter><PoliticaRsAsnBloco {...({ dados: { politicaRs: p } } as any)} /></MemoryRouter>)

describe('bloco Política de roteamento do ASN', () => {
  it('mostra o perfil como inferido com o critério, as ações com a fração das rotas e os motivos com amostra de prefixos', () => {
    montar(pol)
    const bloco = screen.getByTestId('politica-rs-df')
    expect(bloco.textContent).toContain('Perfil seletivo (inferido)')
    expect(bloco.textContent).toContain("ação 'nao_exportar_para' em 30% das rotas")
    expect(screen.getByText('AS64510').getAttribute('href')).toBe('/asn/64510')
    expect(screen.getByText('30%')).toBeTruthy()
    expect(screen.getByText('<1%')).toBeTruthy()          // fração pequena não vira 0%
    expect(bloco.textContent).toContain('Invalid on RPKI')
    expect(bloco.textContent).toContain('198.18.0.0/32, 198.18.0.1/32')
    expect(document.body.textContent).toMatch(/equivalência assumida pela forma/)
    expect(document.body.textContent).toMatch(/Evidência do route server \(insumo da prontidão, não veredito sobre o AS\): 40 rotas rejeitadas/)
    expect(screen.getByText('Explorador de communities').getAttribute('href')).toBe('/communities')
    expect(document.body.textContent).not.toMatch(/culpa|irregular|pior|melhor|suspeito/i)
  })

  it('sem perfil mostra indeterminado e diz quando não há ação de exportação', () => {
    const p = { ...pol, ixps: { df: { politica: { ...pol.ixps.df.politica!, perfil: null, perfil_criterio: 'menos de 10 rotas recebidas coletadas (5)', acoes: {} } } } } as PoliticaAsn
    montar(p)
    expect(screen.getByText(/Perfil indeterminado/)).toBeTruthy()
    expect(screen.getByText(/Nenhuma community de ação de exportação/)).toBeTruthy()
  })
})
