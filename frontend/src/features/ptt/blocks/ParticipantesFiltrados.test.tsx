// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { ParticipantesFiltradosBloco } from './ParticipantesFiltradosBloco'

const dados = {
  ixp: { asn_members: [64496, 64497, 64498, 64499] },
  mergedV4: { asn_direct: [64496, 64497, 64498] }, mergedV6: { asn_direct: [64496] },
  membersData: { nomes: { '64496': { name: 'REDE A', uf: 'SP' }, '64497': { name: 'REDE B', uf: 'RJ' }, '64498': { name: 'REDE C', uf: 'SP' }, '64499': { name: 'REDE D', uf: 'RJ' } } },
  routeServers: { membros: [{ asn: 64498, cadastrado_sem_sessao: true }] },
} as any
const montar = () => render(<MemoryRouter><ParticipantesFiltradosBloco {...({ dados } as any)} /></MemoryRouter>)
const asns = () => Array.from(document.querySelectorAll('tbody tr td:first-child')).map((t) => t.textContent)

describe('participantes com filtros do PTT', () => {
  it('lista membros e diretos e filtra por família de IP, route server e UF de origem', () => {
    montar()
    expect(asns()).toEqual(['AS64496', 'AS64497', 'AS64498', 'AS64499'])
    fireEvent.click(screen.getByText('Sem IPv6'))
    expect(asns()).toEqual(['AS64497', 'AS64498', 'AS64499'])
    fireEvent.click(screen.getByText('Cadastrados sem sessão com o route server'))
    expect(asns()).toEqual(['AS64498'])
    fireEvent.click(screen.getByText('Todos'))
    fireEvent.change(screen.getByLabelText(/UF de origem/), { target: { value: 'RJ' } })
    expect(asns()).toEqual(['AS64497', 'AS64499'])
    fireEvent.click(screen.getByText('Sem peering direto'))
    expect(asns()).toEqual(['AS64499'])
  })
})
