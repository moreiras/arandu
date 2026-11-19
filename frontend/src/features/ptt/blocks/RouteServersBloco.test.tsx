// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { RouteServersBloco } from './RouteServersBloco'
import type { RouteServersIxp } from '../../../types/api'

const rs: RouteServersIxp = {
  snapshot_date: '2026-10-31', coletado_em: '2026-10-31T22:54:20Z', fonte: 'https://lg.ix.br (Alice-LG)', versao_alice: '6.1.0', parametros: { dias_down: 7, uso_limite: 0.8, idade_max_vizinhos_h: 24 },
  limites: 'Estado do route server no instante da coleta. Cadastrado sem sessão pode ser peering bilateral.', nome: 'IX.br São Paulo',
  rs: [
    { rs: 'SP-rs1-v4', numero: 'rs1', afi: 'v4', estado_rotas: 'BUSY', rotas_atualizadas_em: '2026-10-26T22:19:37Z', vizinhos_em: '2026-10-31T22:50:00Z', vizinhos_incerto: false, rotas_importadas: 0, consultado: true, erro: null, sessoes: 3, sessoes_up: 2 },
    { rs: 'SP-rs2-v4', numero: 'rs2', afi: 'v4', estado_rotas: 'READY', rotas_atualizadas_em: '2026-10-30T04:00:00Z', vizinhos_em: '2026-10-29T04:00:00Z', vizinhos_incerto: true, rotas_importadas: 800, consultado: true, erro: null, sessoes: 3, sessoes_up: 3 },
  ],
  resumo: { rs: 2, rs_consultados: 2, rs_rotas_prontas: 1, rs_vizinhos_atuais: 1, cadastrados: 4, cadastrados_com_sessao: 3, cadastrados_sem_sessao: 1, sessao_sem_cadastro: 1, sessoes: 6, sessoes_up: 5, sessoes_down: 1,
    membros_down: 1, membros_com_rs_incerto: 0, membros_perto_do_limite: 1 },
  membros_listados: 'destaque', membros_total: 9,
  membros: [
    { asn: 64496, nome: 'REDE EXEMPLO A', cadastrado: true, sessoes: 2, up: 0, down: 2, down_certo: 2, max_dias_down: 205, todas_down: true, membro_down: true, perto_do_limite: false },
    { asn: 64497, nome: 'REDE EXEMPLO B', cadastrado: true, sessoes: 2, up: 2, down: 0, down_certo: 0, max_uso_limite: 0.9, todas_down: false, membro_down: false, perto_do_limite: true },
    { asn: 64498, nome: 'REDE EXEMPLO C', cadastrado: true, sessoes: 0, up: 0, down: 0, down_certo: 0, todas_down: false, membro_down: false, perto_do_limite: false, cadastrado_sem_sessao: true },
  ],
}
const ctx = (r: RouteServersIxp) => ({ dados: { routeServers: r, code: 'sp' } } as any)
const montar = (r: RouteServersIxp) => render(<MemoryRouter><RouteServersBloco {...ctx(r)} /></MemoryRouter>)

describe('bloco Route servers do PTT', () => {
  it('mostra números medidos com a data da coleta, o aviso do route server sem sessões atuais, o estado do cache de rotas como informação à parte e o cadastrado sem sessão como possível bilateral', () => {
    montar(rs)
    expect(screen.getByText('1 de 2')).toBeTruthy()                                       // route servers com sessões atuais
    expect(screen.getByText('5 de 6')).toBeTruthy()                                       // sessões no ar
    expect(screen.getByText(/SP-rs2-v4 \(sessões atualizadas em 2026-10-29 04:00 UTC\)/)).toBeTruthy()      // só o de vizinhos velhos: o BUSY das rotas não avisa
    expect(document.body.textContent).not.toMatch(/SP-rs1-v4 \(sessões/)
    expect(screen.getByText(/não diz nada das sessões/)).toBeTruthy()
    expect(screen.getByText('AS64496').getAttribute('href')).toBe('/asn/64496')
    expect(screen.getByText('205')).toBeTruthy()
    expect(screen.getByText(/Cadastrados no IX\.br sem sessão nos route servers \(1\): AS64498/)).toBeTruthy()
    expect(screen.getByText(/Pode ser peering bilateral/)).toBeTruthy()
    expect(screen.getByText(/Coletado em 2026-10-31 22:54 UTC/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/falhou|culpa|irregular|pior|melhor/i)
  })

  it('limita a lista e leva à aba de Rankings do PTT', () => {
    const muitos = Array.from({ length: 20 }, (_, i) => ({ asn: 65000 + i, nome: `M${i}`, cadastrado: true, sessoes: 1, up: 0, down: 1, down_certo: 1, max_dias_down: 8 + i, todas_down: true, membro_down: true, perto_do_limite: false }))
    montar({ ...rs, membros: muitos })
    expect(screen.getByText(/e mais 5\./)).toBeTruthy()
    expect(screen.getByText('Ver a lista em Rankings').getAttribute('href')).toBe('/rankings?aba=route-servers&ixp=sp')
  })
})
