// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { presencaIxbr } from './CDNCapPage'

const pres = (direct: boolean, origin: boolean) => ({ v4: { direct, origin }, v6: { direct: false, origin } })

describe('presença de CDN no IX.br por critério (CDN-E1)', () => {
  it('separa membro do cadastro, sessão no route server e vista só por terceiros', () => {
    // sessão em sp e rj; origem também em ce e mg sem sessão; cadastro em sp, rj, fec e gyn
    const docs = [{ ixp_presence: { sp: pres(true, true), ce: pres(false, true) } }, { ixp_presence: { rj: pres(true, false), mg: pres(false, true), sp: pres(false, true) } }]
    expect(presencaIxbr(docs as any, ['sp', 'rj', 'fec', 'gyn'])).toEqual({ membro: 4, sessao: 2, terceiros: 2 })
  })

  it('bordas: sem sessão nenhuma (só terceiros) e sem documento', () => {
    expect(presencaIxbr([{ ixp_presence: { sp: pres(false, true), rj: pres(false, true) } }] as any, [])).toEqual({ membro: 0, sessao: 0, terceiros: 2 })
    expect(presencaIxbr([], ['sp'])).toEqual({ membro: 1, sessao: 0, terceiros: 0 })
  })
})
