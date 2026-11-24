// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { contraste } from '../../lib/contraste'
import { HilbertMapV6 } from './HilbertMapV6'
import { V6_LAYER_META } from './HilbertMapV6Block'

beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} }) })

const hex = (rgb: string) => {
  const m = rgb.match(/\d+/g)
  return m ? `#${m.slice(0, 3).map((v) => Number(v).toString(16).padStart(2, '0')).join('')}` : rgb
}

describe('seletor de camada do Hilbert (contraste do botão ativo, /panorama/ipv6)', () => {
  it('cada camada ativa tem texto branco com contraste ≥ 4,5:1 e aria-pressed', () => {
    render(<HilbertMapV6 data={null} />)
    for (const meta of Object.values(V6_LAYER_META)) {
      const b = screen.getByRole('button', { name: meta.label })
      fireEvent.click(b)
      expect(b).toHaveAttribute('aria-pressed', 'true')
      expect(b).toHaveAttribute('type', 'button')
      expect(contraste('#ffffff', hex(b.style.backgroundColor)), meta.label).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('os seletores do IPv4 (panorama e painel) usam a mesma cor legível', () => {
    for (const f of ['../../features/panorama/SecoesHilbert.tsx', '../../pages/Dashboard.tsx']) {
      expect(readFileSync(resolve(__dirname, f), 'utf-8'), f).toContain('backgroundColor: corLegivel(meta.color)')
    }
  })
})
