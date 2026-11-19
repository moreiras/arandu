// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { RouteServersAsnBloco } from './RouteServersAsnBloco'
import type { RouteServersAsn } from '../../../types/api'

const rs: RouteServersAsn = {
  snapshot_date: '2026-10-31', coletado_em: '2026-10-31T22:54:20Z', fonte: 'https://lg.ix.br (Alice-LG)', versao_alice: '6.1.0', parametros: { dias_down: 7, uso_limite: 0.8, idade_max_vizinhos_h: 24 },
  limites: 'Sessão down não diz de quem é a causa.',
  total: { ixps: 2, sessoes: 3, up: 2, down: 1, ixps_down: 0, ixps_perto_do_limite: 0 },
  ixps: {
    sp: { cadastrado: true, sessoes: 2, up: 1, down: 1, down_certo: 1, max_dias_down: 3, todas_down: false, membro_down: false, perto_do_limite: false, lista: [
      { rs: 'SP-rs1-v4', afi: 'v4', ip: '203.0.113.10', estado: 'down', dias: 3, erro: 'BGP Error: Hold timer expired', recebidas: 0, aceitas: 0, filtradas: 0, limite: 100, uso_limite: 0 },
      { rs: 'SP-rs2-v4', afi: 'v4', ip: '203.0.113.11', estado: 'up', dias: 40, recebidas: 10, aceitas: 9, filtradas: 1, limite: 100, uso_limite: 0.1, rs_incerto: true },
    ] },
    rj: { cadastrado: false, sessoes: 1, up: 1, down: 0, down_certo: 0, max_uso_limite: 0.5, todas_down: false, membro_down: false, perto_do_limite: false, lista: [
      { rs: 'RJ-rs1-v6', afi: 'v6', ip: '2001:db8::1', estado: 'up', dias: 9, recebidas: 50, aceitas: 50, filtradas: 0, limite: 100, uso_limite: 0.5 },
    ] },
  },
}

describe('bloco Nos route servers do ASN', () => {
  it('mostra por PTT as sessões, o último erro reportado e marca a sessão sem frescor confirmado como incerta', () => {
    render(<MemoryRouter><RouteServersAsnBloco {...({ dados: { routeServers: rs } } as any)} /></MemoryRouter>)
    expect(screen.getByText(/3 sessões em 2 PTT\(s\): 2 up e 1 down/)).toBeTruthy()
    expect(screen.getByText('SP').getAttribute('href')).toBe('/ixp/sp')
    expect(screen.getByText('sem cadastro no IX.br')).toBeTruthy()
    expect(screen.getByText('50%')).toBeTruthy()
    expect(screen.getByText('BGP Error: Hold timer expired')).toBeTruthy()
    expect(screen.getByText(/up \(sem frescor confirmado: incerta\)/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/falhou|culpa|irregular/i)
  })
})
