// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExternalIXPRouteServer, type DecixRouteServer } from './ExternalIXPRouteServer'

const base: DecixRouteServer = {
  coletado_em: '2026-11-10T12:00:00Z', rotas_coletadas_em: '2026-11-10T12:30:00Z', fonte: 'https://lg.de-cix.net (Alice-LG)', versao_alice: '6.2.0', aviso: 'Sessão BGP no route server; a origem é um piso.',
  cidade: 'São Paulo', criterio: { asn_direct: 'sessão up no route server', asn_origin: 'último ASN do AS_PATH das rotas lidas' },
  resumo: { rs: 4, rs_consultados: 4, sessoes: 5, sessoes_up: 4, sessoes_down: 1, membros: 4, membros_up: 3, asn_direct_count: 3, br_asn_direct_count: 2, asn_origin_count: 7, br_asn_origin_count: 5 },
  asn_direct: [64496, 64497, 64499],
  rotas: { parcial: true, vizinhos_lidos: 2, vizinhos_completos: 1, herdados: 0, rotas_total_dos_lidos: 603, rotas_lidas: 503, cobertura: { elegiveis: 3, lidos_na_rodada: 2, herdados: 0, sem_leitura: 1, idade_max_dias: 0 } },
  peeringdb: { cadastrados: 3, cadastrados_sem_sessao_up_total: 1, sessao_up_sem_cadastro_total: 1 },
  comparacao_cidade: {
    cidade: 'São Paulo', ixbr: { ptt: 'sp', asn_direct: 5, br_asn_origin: 2 }, decix: { ptt: 'decix-sp', asn_direct: 3, br_asn_direct: 2, asn_origin_piso: 7 },
    interseccao_direct: { ambos: 2, so_decix: 1, so_ixbr: 3, pct_do_decix_no_ixbr: 66.7 }, no_decix_sem_ixbr: { total: 1, asns: [64499], truncado: false },
    externos: { 'equinix-sp': { membros_peeringdb: 3, ambos_decix_sessao: 2, ambos_ixbr: 2 } },
  },
}

describe('cartões do route server do DE-CIX', () => {
  it('mostra sessões, diretos e origem como piso, com a cobertura e os critérios', () => {
    render(<ExternalIXPRouteServer rs={base} />)
    expect(screen.getByText('4 / 5')).toBeTruthy()
    expect(screen.getByText('ASNs de origem (piso)')).toBeTruthy()
    expect(screen.getByText(/leitura parcial: é um mínimo/)).toBeTruthy()
    expect(screen.getByText(/2 nesta coleta, 0 herdados de coletas anteriores e 1 ainda sem leitura, de 3 vizinhos/)).toBeTruthy()
    expect(screen.getByText(/sessão up no route server\./)).toBeTruthy()
  })

  it('compara com o IX.br da cidade sem dizer que é tráfego, e lista os ASNs só do DE-CIX com link', () => {
    render(<ExternalIXPRouteServer rs={base} />)
    const tabela = screen.getByTestId('comparacao-cidade')
    expect(tabela.textContent).toContain('IX.br SP')
    expect(tabela.textContent).toContain('equinix-sp')
    expect(tabela.textContent).toContain('66,7% dos ASNs do DE-CIX também estão no IX.br')
    expect(tabela.textContent).toContain('não de tráfego')
    expect(screen.getByText('AS64499').getAttribute('href')).toBe('/asn/64499')
  })

  it('sem PTT do IX.br na cidade não inventa comparação e mostra o aviso de bloqueio', () => {
    const rs = { ...base, bloqueio: { motivo: 'HTTP 429' }, comparacao_cidade: { ...base.comparacao_cidade, ixbr: null, interseccao_direct: undefined, no_decix_sem_ixbr: undefined } }
    render(<ExternalIXPRouteServer rs={rs} />)
    expect(screen.getByText(/sinal de bloqueio do servidor \(HTTP 429\)/)).toBeTruthy()
    expect(screen.queryByText(/IX\.br SP/)).toBeNull()
    expect(screen.queryByText(/ASNs estão nos dois/)).toBeNull()
  })
})
