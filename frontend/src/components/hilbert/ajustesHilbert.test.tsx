// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import docBase from '../../test/fixtures/asn_detail.json'
import { HilbertIpv6Bloco } from '../../features/asn/blocks/CurvaHilbertAsnBloco'
import { contraste, corLegivel } from '../../lib/contraste'
import { LAYER_META } from './HilbertMap16'
import { HilbertMapV6 } from './HilbertMapV6'
import { V6_LAYER_META } from './HilbertMapV6Block'
import { COR_ALOCADO_VISIVEL, OPACIDADE_MIN, opacidadeDensidade, V6_BLOCKS } from './hilbert'
import { ZoomModalDashV4, ZoomModalV6 } from './IXPHilbertZoom'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

const dados = (doc: any) => ({ doc, date: '2026-09-20', ixpPaths: {}, pathNodeMeta: {}, ixpMemberCodes: [], carregandoCaminhos: false })
const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!

describe('curva IPv6 do AS mostra todos os blocos (item 1)', () => {
  it('AS só com 2001::/16 (Legado) mostra o mesmo número de blocos do panorama, com os do AS destacados', () => {
    const doc: any = { ...docBase, asn: 22548, rir_prefixes_v6: ['2001:12ff::/32'], global_prefixes_v6: ['2001:12ff::/32'], ixp_presence: {} }
    const { unmount } = render(<HilbertMapV6 data={null} />)
    const noPanorama = V6_BLOCKS.filter((b) => screen.queryAllByText(b.label).length > 0).length
    unmount()
    render(<HilbertIpv6Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    const noAs = V6_BLOCKS.filter((b) => screen.queryAllByText(b.label).length > 0).length
    expect(noPanorama).toBe(V6_BLOCKS.length)
    expect(noAs).toBe(noPanorama)
    expect(screen.getAllByRole('img')).toHaveLength(V6_BLOCKS.length)
    expect(screen.getByRole('img', { name: /bloco 2001::\/16 \(Legado\).*: 1 prefixo\./ })).toBeTruthy()
    expect(screen.getByRole('img', { name: /bloco 2800::\/12 \(LACNIC\).*: 0 prefixos\./ })).toBeTruthy()
  })
})

describe('cor de "alocado e visível" (item 2)', () => {
  it('é ciano nas duas camadas do panorama e na curva do AS, sem vermelho, com botão ativo AA', () => {
    expect(LAYER_META.rir_br_visible.color).toBe(COR_ALOCADO_VISIVEL)
    expect(V6_LAYER_META.rir_br_visible.color).toBe(COR_ALOCADO_VISIVEL)
    for (const m of [...Object.values(LAYER_META), ...Object.values(V6_LAYER_META)]) expect(m.color.toLowerCase(), m.label).not.toBe('#ef4444')
    const doc: any = { ...docBase, asn: 64496, rir_prefixes_v6: ['2804:1234::/32'], global_prefixes_v6: ['2804:1234::/32'], ixp_presence: {} }
    render(<HilbertIpv6Bloco dados={dados(doc) as any} snapshot="2026-09-20" />)
    const botao = screen.getByRole('button', { name: 'Alocado e visível' })
    fireEvent.click(botao)
    const m = botao.style.backgroundColor.match(/\d+/g)!.slice(0, 3).map((v) => Number(v).toString(16).padStart(2, '0')).join('')
    expect(`#${m}`).toBe(corLegivel(COR_ALOCADO_VISIVEL))
    expect(contraste('#ffffff', `#${m}`)).toBeGreaterThanOrEqual(4.5)
  })
})

describe('plural nos zooms (item 3a)', () => {
  const wrap = (el: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>

  it('IPv4: "1 bloco /16" e "2 blocos /16"', () => {
    const dens = (n: number) => { const d = new Array<number>(65536).fill(0); for (let i = 0; i < n; i++) d[i] = 3; return d }
    const um = render(wrap(<ZoomModalDashV4 sx={0} sy={0} slashEight={0} activeLayer="rir_br" layerColor="#3b82f6" density={dens(1)} semDetalhe onClose={() => {}} />))
    expect(screen.getByRole('dialog').textContent).toContain('1 bloco /16')
    expect(screen.getByRole('dialog').textContent).not.toContain('1 blocos')
    um.unmount()
    render(wrap(<ZoomModalDashV4 sx={0} sy={0} slashEight={0} activeLayer="rir_br" layerColor="#3b82f6" density={dens(2)} semDetalhe onClose={() => {}} />))
    expect(screen.getByRole('dialog').textContent).toContain('2 blocos /16')
  })

  it('IPv6: "1 bloco /32" e "2 blocos /32"', () => {
    const modal = (cells: number[]) => <ZoomModalV6 config={lacnic} gx={0} gy={0} allCells={cells} ownCells={null} thirdCells={null} isPeerMode={false} onClose={() => {}} />
    const um = render(modal([0]))
    expect(screen.getByRole('dialog').textContent).toContain('1 bloco /32')
    expect(screen.getByRole('dialog').textContent).not.toContain('1 blocos')
    um.unmount()
    render(modal([0, 1]))
    expect(screen.getByRole('dialog').textContent).toContain('2 blocos /32')
  })
})

describe('intensidade mínima (item 3b)', () => {
  it('célula com dado nunca fica abaixo do mínimo, sem dado é 0 e a ordem relativa se mantém', () => {
    expect(opacidadeDensidade(0)).toBe(0)
    expect(opacidadeDensidade(1)).toBeGreaterThanOrEqual(OPACIDADE_MIN)
    expect(OPACIDADE_MIN).toBeGreaterThanOrEqual(0.5)
    let anterior = 0
    for (let n = 1; n <= 256; n++) {
      const o = opacidadeDensidade(n)
      expect(o).toBeGreaterThan(anterior)
      expect(o).toBeLessThanOrEqual(1)
      anterior = o
    }
    expect(opacidadeDensidade(1000)).toBe(opacidadeDensidade(256))
  })
})
