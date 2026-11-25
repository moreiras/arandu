// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { RejeicoesBloco } from './RejeicoesBloco'
import type { RejeicoesIxp } from '../../../types/api'

const rj: RejeicoesIxp = {
  snapshot_date: '2026-11-05', coletado_nivel2: '2026-11-06T22:00:00Z', coletado_nivel3: '2026-11-06T22:10:00Z', fonte: 'https://lg.ix.br (Alice-LG)', versao_alice: '6.1.0',
  parametros: { amostra_prefixos: 5, min_rotas_perfil: 10, fracao_seletivo: 0.1, fracao_restritivo: 0.5, alvos_restritivo: 50 }, limites: 'Só dos vizinhos coletados; o perfil é inferido.', ixp: 'df', nome: 'IX.br Brasília',
  rejeicoes: { cobertura: { elegiveis: 104, coletados: 100, herdados: 0 }, asns_com_rejeicao: 2, rotas_rejeitadas: 43, rotas_com_motivo_decodificado: 43, soma_dos_motivos: 43,
    por_motivo: [{ codigo: '26162:300:0', rotulo: 'Invalid on RPKI', classe: 'rejeicao', rotas: 25, asns: 1 }, { codigo: '26162:190:1', rotulo: 'Bogon prefix', classe: 'rejeicao', rotas: 10, asns: 1 }],
    asns_total: 2, asns: [{ asn: 64498, nome: 'REDE A', rotas: 40, motivos: { '26162:300:0': 25 } }, { asn: 64499, rotas: 3, motivos: { '26162:616:666': 3 } }] },
  politica: { cobertura: { elegiveis: 452, coletados: 452, herdados: 0 }, asns_com_dado: 3, perfis: { aberto: 1, restritivo: 1, seletivo: 1 }, acoes: { nao_exportar_para: { asns: 1 } }, blackhole: { asns: 1, rotas: 2 },
    rpki: { valid: 240, unknown: 10, not_checked: 0, invalid: 0 } },
}
const montar = (r: RejeicoesIxp) => render(<MemoryRouter><RejeicoesBloco {...({ dados: { rejeicoes: r, code: 'df' } } as any)} /></MemoryRouter>)

describe('bloco Rejeições do PTT', () => {
  it('mostra a cobertura da coleta, os motivos decodificados, os perfis como inferidos e o caminho para o explorador', () => {
    montar(rj)
    expect(screen.getByText(/Rejeições \(nível 2\): 100 de 104 vizinhos coletados/)).toBeTruthy()
    expect(screen.getByText('Invalid on RPKI', { exact: false })).toBeTruthy()
    expect(screen.getByText('AS64498').getAttribute('href')).toBe('/asn/64498')
    expect(document.body.textContent).toMatch(/Perfis inferidos: 1 aberto, 1 restritivo, 1 seletivo/)
    expect(screen.getByText('Communities usadas neste PTT').getAttribute('href')).toBe('/communities?ixp=df')
    expect(document.body.textContent).not.toMatch(/culpa|irregular|pior|melhor|suspeito/i)
  })

  it('sem nenhuma coleta diz isso, em vez de mostrar zeros', () => {
    montar({ ...rj, rejeicoes: null, politica: null })
    expect(screen.getByText(/Sem coleta de rotas dos route servers deste PTT/)).toBeTruthy()
  })

  it('IXP-E4: a faixa diz quantos foram lidos na rodada, quantos vêm de rodadas anteriores e a idade da leitura mais antiga', () => {
    montar({ ...rj,
      rejeicoes: { ...rj.rejeicoes!, cobertura: { elegiveis: 80, coletados: 0, herdados: 80, lidos_na_rodada: 0, sem_leitura: 0, idade_max_dias: 12, pulados_lentos: 0 } },
      politica: { ...rj.politica!, cobertura: { elegiveis: 80, coletados: 60, herdados: 15, lidos_na_rodada: 60, sem_leitura: 5, idade_max_dias: 1, pulados_lentos: 5 } } })
    const t = document.body.textContent ?? ''
    expect(t).toMatch(/0 de 80 vizinhos lidos nesta rodada, 80 mantidos de rodadas anteriores, 0 sem leitura \(leitura mais antiga com 12 dias\)/)
    expect(t).toMatch(/60 de 80 vizinhos lidos nesta rodada, 15 mantidos de rodadas anteriores, 5 sem leitura \(leitura mais antiga com 1 dia; 5 fora da rodada/)
    expect(t).not.toMatch(/0 de 80 vizinhos coletados/)
  })
})
