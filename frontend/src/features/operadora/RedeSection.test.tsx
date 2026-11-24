// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { OperadoraRede } from '../../types/api'
import { RedeSection } from './RedeSection'

const asn = (n: number) => ({ asn: n, name: `Rede ${n}`, apnic_users: 10, rir_prefixes_v6_count: 1, rir_prefixes_v4_count: 1, has_rpki: true, has_aspa: false, ixps_direct_count: 1, alerts_count: 1 })
const rede = {
  asn_count: 2, total_apnic_users: 20, total_apnic_v6_users: 5, total_rir_prefixes_v6: 2, total_rir_prefixes_v4: 2, ixps_direct: ['sp'],
  has_rpki: true, has_aspa: false,
  alertas: { total: 2, por_categoria: [{ category: 'rpki', severity: 'aviso', count: 2, asns: [{ asn: 64500, title: 'Prefixo sem ROA' }, { asn: 64501, title: 'ROA inválido' }] }] },
  asns: [asn(64500), asn(64501)],
} as unknown as OperadoraRede

const montar = () => render(<MemoryRouter><RedeSection rede={rede} /></MemoryRouter>)

describe('RedeSection: estado e informação acessíveis (OPERADORA-E4, OPERADORA-E5)', () => {
  it('os ASNs de cada alerta ficam no conteúdo (details), não só no title', () => {
    montar()
    const item = screen.getByTestId('alerta-categoria')
    expect(item.tagName).toBe('DETAILS')
    expect(item).not.toHaveAttribute('title')
    expect(within(item).getByText(/Prefixo sem ROA/)).toBeInTheDocument()
    expect(within(item).getByRole('link', { name: 'AS64501' })).toHaveAttribute('href', '/asn/64501')
  })

  it('o botão da tabela por ASN tem aria-expanded e só aponta aria-controls para a tabela quando ela existe', () => {
    montar()
    const botao = screen.getByRole('button', { name: /detalhe por ASN/ })
    expect(botao).toHaveAttribute('type', 'button')
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(botao).not.toHaveAttribute('aria-controls')
    fireEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    const alvo = document.getElementById(botao.getAttribute('aria-controls')!)
    expect(alvo).not.toBeNull()
    const tabela = within(alvo!).getByRole('table')
    expect(tabela.querySelector('caption')).toHaveTextContent('Detalhe por ASN')
    for (const th of within(tabela).getAllByRole('columnheader')) expect(th).toHaveAttribute('scope', 'col')
  })
})
