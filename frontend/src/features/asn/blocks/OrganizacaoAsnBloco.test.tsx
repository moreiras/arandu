// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { OrganizacaoAsnBloco } from './OrganizacaoAsnBloco'
import type { AbusoAsn, OrganizacaoAsn } from '../../../types/api'

const org: OrganizacaoAsn = {
  snapshot_date: '2026-11-05', coletado_em: '2026-11-06T21:04:00Z', fonte: { nome: 'CAIDA AS Rank', citacao: 'The CAIDA UCSD AS Rank' }, limites: 'Organização inferida pelo CAIDA; não é grupo societário.',
  org_id: 'aaaa', org_nome: 'Provedor Exemplo Ltda', org_pais: 'BR', membros_total: 3, irmaos_br: [64499],
}
const abuso: AbusoAsn = {
  snapshot_date: '2026-11-05', coletado_em: '2026-11-06T21:01:00Z', fonte: { nome: 'Feodo Tracker (abuse.ch)', licenca: 'CC0' }, limites: 'Nenhum registrado não quer dizer rede limpa.',
  registrado: false, feodo_total_mundo: 5, feodo_c2: 0, feodo_c2_online: 0, feodo_malware: {},
}

describe('bloco Organização e abuso do ASN', () => {
  it('mostra a organização, os irmãos com link e a contagem de C2 sem dizer que a rede é limpa', () => {
    render(<MemoryRouter><OrganizacaoAsnBloco {...({ dados: { organizacao: org, abuso } } as any)} /></MemoryRouter>)
    expect(screen.getByText('Provedor Exemplo Ltda')).toBeTruthy()
    expect(screen.getByText('AS64499').getAttribute('href')).toBe('/asn/64499')
    expect(screen.getByText(/nenhum na lista/)).toBeTruthy()
    expect(screen.getByText(/não é grupo societário/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/rede limpa\.?\s*$|culpa|malicios/i)
  })

  it('funciona só com o abuso, quando o CAIDA não conhece o ASN', () => {
    render(<MemoryRouter><OrganizacaoAsnBloco {...({ dados: { organizacao: null, abuso: { ...abuso, registrado: true, feodo_c2: 2, feodo_c2_online: 1 } } } as any)} /></MemoryRouter>)
    expect(screen.getByText(/\(1 online\)/)).toBeTruthy()
    expect(screen.queryByTestId('irmaos')).toBeNull()
  })
})
