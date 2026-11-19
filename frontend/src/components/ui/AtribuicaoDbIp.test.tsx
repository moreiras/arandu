// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProvenienciaCompacta } from './ProvenienciaCompacta'
import { usaDbIp } from '../../lib/atribuicoes'

describe('atribuição do DB-IP (licença do DB-IP Lite: link na página que usa a base)', () => {
  it('bloco com fonte do DB-IP mostra o link visível, fora do popover', () => {
    render(<ProvenienciaCompacta bloco={{ fontes: ['registro_br', 'prefix_geo'], selo: 'inferido' }} />)
    const link = screen.getByRole('link', { name: 'IP Geolocation by DB-IP' })
    expect(link.getAttribute('href')).toBe('https://db-ip.com')
    expect(link.closest('details')).toBeNull()
  })

  it('bloco sem fonte do DB-IP não mostra o link', () => {
    render(<ProvenienciaCompacta bloco={{ fontes: ['registro_br'] }} />)
    expect(screen.queryByRole('link', { name: 'IP Geolocation by DB-IP' })).toBeNull()
  })

  it('as duas fontes de geolocalização por IP do catálogo exigem o link', () => {
    expect(usaDbIp(['global_prefix_geo'])).toBe(true)
    expect(usaDbIp(['cnpj_geo'])).toBe(false)
    expect(usaDbIp(undefined)).toBe(false)
  })
})
