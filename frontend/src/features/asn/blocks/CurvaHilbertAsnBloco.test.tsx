// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import docBase from '../../../test/fixtures/asn_detail.json'
import { abasDe, blocosDe } from '../../entidade/registry'
import '../index'
import { HilbertIpv4Bloco, HilbertIpv6Bloco } from './CurvaHilbertAsnBloco'
import { V6_BLOCKS } from '../../../components/hilbert/hilbert'

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
      expect(b.comoLer).toContain(id === 'hilbert-ipv6' ? '/32' : '/16')
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

describe('curvas de Hilbert do AS (os mesmos mapas do panorama técnico)', () => {
  beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

  it('IPv4: canvas com nome acessível, camadas do AS em botões com aria-pressed, legenda e lista como alternativa textual', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    expect(screen.getByRole('img', { name: /Curva de Hilbert IPv4 do AS64496, camada "Alocado pelo Registro\.br".*lista de prefixos abaixo/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Alocado pelo Registro.br' })).toHaveAttribute('aria-pressed', 'true')
    for (const n of ['Visto na tabela global', 'Alocado e visível', 'Visto no PTT do IX.br']) {
      expect(screen.getByRole('button', { name: n })).toHaveAttribute('aria-pressed', 'false')
    }
    expect(screen.getByText(/Prefixos IPv4 do AS64496 alocados pelo Registro\.br/)).toBeTruthy()
    const lista = screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })
    expect(within(lista).getByText('198.18.0.0/16')).toBeTruthy()
    expect(within(lista).queryByText('203.0.113.0/24')).toBeNull()
  })

  it('IPv4: a camada escolhida decide a lista; "alocado e visível" é a interseção e cada prefixo traz suas origens em texto', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    fireEvent.click(screen.getByRole('button', { name: 'Visto na tabela global' }))
    const lista = () => screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })
    expect(within(lista()).getByText('203.0.113.0/24')).toBeTruthy()
    expect(within(lista()).getByText('198.18.4.0/24')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Alocado e visível' }))
    expect(within(lista()).getByText('198.18.4.0/24')).toBeTruthy()   // dentro do /16 alocado
    expect(within(lista()).queryByText('203.0.113.0/24')).toBeNull()
    expect(lista().textContent).toMatch(/visto na tabela global, visto em PTT do IX\.br/)
  })

  it('IPv4: escolher um quadrante /8 filtra a lista e "limpar filtro" volta', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    fireEvent.click(screen.getByRole('button', { name: 'Visto na tabela global' }))
    fireEvent.click(screen.getByRole('button', { name: /^203\.0\.0\.0\/8/ }))
    const lista = screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })
    expect(within(lista).queryByText('198.18.4.0/24')).toBeNull()
    expect(within(lista).getByText('203.0.113.0/24')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'limpar filtro' }))
    expect(within(screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })).getByText('198.18.4.0/24')).toBeTruthy()
  })

  it('o PTT escolhido restringe a camada de PTT; sem escolha são todos', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    fireEvent.click(screen.getByRole('button', { name: 'Visto no PTT do IX.br' }))
    const lista = () => screen.getByRole('list', { name: 'Prefixos IPv4 do AS64496' })
    expect(within(lista()).getByText('203.0.113.0/24')).toBeTruthy()
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'sp' } })
    expect(screen.getByRole('button', { name: 'Visto no PTT SP' })).toHaveAttribute('aria-pressed', 'true')
    expect(within(lista()).queryByText('203.0.113.0/24')).toBeNull()
    expect(within(lista()).getByText('198.18.5.0/24')).toBeTruthy()
  })

  it('IPv6: todos os blocos de RIR aparecem, como no panorama, com nome acessível, quadrantes /20 e lista da camada', () => {
    render(<HilbertIpv6Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    expect(screen.getAllByRole('img').length).toBe(V6_BLOCKS.length)
    expect(screen.getByRole('img', { name: /Curva de Hilbert IPv6 do AS64496, camada "Alocado pelo Registro\.br", bloco 2800::\/12 \(LACNIC\)/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^2804:1000::\/20/ })).toBeTruthy()
    expect(within(screen.getByRole('list', { name: 'Prefixos IPv6 do AS64496' })).getByText('2804:1234::/32')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Visto no PTT do IX.br' }))
    expect(within(screen.getByRole('list', { name: 'Prefixos IPv6 do AS64496' })).getByText('2804:9999::/32')).toBeTruthy()
  })

  it('os controles próprios são botões reais com altura mínima; o resumo conta os prefixos da camada', () => {
    render(<HilbertIpv4Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    // Os botões de quadrante sobre o mapa só recebem foco do teclado (sem captura do mouse): o alvo do ponteiro é o canvas, então a altura mínima não se aplica.
    for (const b of screen.getAllByRole('button')) if (!b.hasAttribute('data-quadrante')) expect(b.className).toMatch(/min-h-\[2[48]px\]/)
    expect(screen.getByTestId('resumo-curva-v4').textContent).toMatch(/1 prefixo IPv4 na camada "Alocado pelo Registro\.br"/)
  })
})
