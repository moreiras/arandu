// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { contraste } from '../../lib/contraste'
import { SCM_SELO } from './tipos'

describe('contraste do selo SCM do localizador (LOC-E8, NBR 17225 5.11.3)', () => {
  it('texto branco sobre o selo passa de 4,5:1 (a cor do mapa, #a855f7, dava 3,96:1)', () => {
    expect(contraste('#ffffff', SCM_SELO)).toBeGreaterThanOrEqual(4.5)
    expect(contraste('#ffffff', '#a855f7')).toBeLessThan(4.5)
  })

  it('lista e balão usam a cor do selo, não a do mapa', () => {
    for (const f of ['PainelEntidades.tsx', 'balloes.ts']) {
      const fonte = readFileSync(resolve(__dirname, f), 'utf-8')
      expect(fonte, f).not.toMatch(/background:\s*'?#a855f7/)
      expect(fonte, f).toContain('SCM_SELO')
    }
  })
})
