// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import docBase from '../../../test/fixtures/asn_detail.json'
import { abasDe, blocosDe } from '../../entidade/registry'
import '../index'
import { HilbertIpv4Bloco, HilbertIpv6Bloco } from './CurvaHilbertAsnBloco'

const doc: any = {
  ...docBase,
  asn: 64496,
  rir_prefixes_v4: ['198.18.0.0/16'],
  global_prefixes_v4: ['198.18.4.0/24', '203.0.113.0/24'],
  rir_prefixes_v6: ['2804:1234::/32'],
  global_prefixes_v6: ['2804:1234:1::/48', '2804:9999::/32'],
  ixp_presence: {
    sp: { v4: { direct: true, origin: true, prefixes: ['198.18.4.0/24', '198.18.5.0/24'] }, v6: { direct: true, origin: true, prefixes: ['2804:9999::/32'] } },
    rj: { v4: { direct: false, origin: true, prefixes: ['203.0.113.0/24'] }, v6: { direct: false, origin: false, prefixes: [] } },
  },
}
const dados = (d: any) => ({ doc: d, date: '2026-09-20', ixpPaths: {}, pathNodeMeta: {}, ixpMemberCodes: [], carregandoCaminhos: false })

describe('aba Numeração do AS', () => {
  it('fica logo depois de Resumo e reúne a lista do Registro.br (aberta) e as curvas, IPv6 antes de IPv4', () => {
    expect(abasDe('asn').map((a) => a.id).slice(0, 3)).toEqual(['resumo', 'numeracao', 'roteamento'])
    expect(abasDe('asn')[1].rotulo).toBe('Numeração')
    const ids = blocosDe('asn').filter((b) => b.aba === 'numeracao').map((b) => b.id)
    expect(ids).toEqual(['prefixos-rir', 'hilbert-ipv6', 'hilbert-ipv4', 'recursos-ipv4'])
    const rir = blocosDe('asn').find((b) => b.id === 'prefixos-rir')!
    expect(rir.recolhido).toBeFalsy()
    for (const id of ['hilbert-ipv6', 'hilbert-ipv4']) {
      const b = blocosDe('asn').find((x) => x.id === id)!
      expect(b.fontes.length).toBeGreaterThan(0)
      expect(b.selo).toBeTruthy()
      expect(b.comoLer).toContain('não uso nem tráfego')
      expect(b.recolhido).toBeFalsy()
    }
  })

  it('o bloco só se aplica quando o AS tem prefixo da família', () => {
    const sem: any = { ...doc, rir_prefixes_v6: [], global_prefixes_v6: [], ixp_presence: {} }
    const ap = (d: any, id: string) => blocosDe('asn').find((b) => b.id === id)!.aplicavel!({ ...dados(d) } as any)
    expect(ap(doc, 'hilbert-ipv6')).toBe(true)
    expect(ap(sem, 'hilbert-ipv6')).toBe(false)
    expect(ap(sem, 'hilbert-ipv4')).toBe(true)
  })
})

describe('curvas de Hilbert do AS', () => {
  it('IPv4: canvas com nome acessível, camadas com contagem, lista de prefixos como alternativa textual', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    expect(screen.getByRole('img', { name: /Curva de Hilbert IPv4 do AS64496.*lista de prefixos abaixo/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Alocado pelo Registro\.br \(1\)/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Só na tabela global \(1\)/ })).toBeTruthy()   // 198.18.4.0/24 está dentro do /16 alocado
    const lista = screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })
    expect(within(lista).getByText('198.18.0.0/16')).toBeTruthy()
    expect(within(lista).getByText('203.0.113.0/24')).toBeTruthy()
    expect(within(lista).queryByText('198.18.4.0/24')).toBeTruthy()   // visto no PTT (SP)
  })

  it('IPv4: escolher um quadrante /8 filtra a lista e "limpar filtro" volta; camada desligada some da lista', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    fireEvent.click(screen.getByRole('button', { name: /^203\.0\.0\.0\/8/ }))
    const lista = screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })
    expect(within(lista).queryByText('198.18.0.0/16')).toBeNull()
    expect(within(lista).getByText('203.0.113.0/24')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'limpar filtro' }))
    expect(within(screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })).getByText('198.18.0.0/16')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Alocado pelo Registro\.br/ }))
    expect(within(screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })).queryByText('198.18.0.0/16')).toBeNull()
  })

  it('IPv6: canvas por bloco de RIR com nome acessível, quadrantes /20 e PTT escolhido', () => {
    render(<HilbertIpv6Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    expect(screen.getByRole('img', { name: /Curva de Hilbert IPv6 do AS64496, bloco 2800::\/12 \(LACNIC\)/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Visto no PTT SP \(1\)/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^2804:1000::\/20/ })).toBeTruthy()
    const lista = screen.getByRole('list', { name: 'Prefixos IPv6 do AS64496' })
    expect(within(lista).getByText('2804:1234::/32')).toBeTruthy()
    expect(within(lista).getByText('2804:9999::/32')).toBeTruthy()
  })

  it('os controles são botões reais com altura mínima e o título da camada não depende só de cor', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    for (const b of screen.getAllByRole('button')) expect(b.className).toMatch(/min-h-\[2[48]px\]/)
    expect(screen.getByRole('button', { name: /Alocado pelo Registro\.br/ }).textContent).toMatch(/\(\d+\)/)
  })
})
