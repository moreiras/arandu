// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import type { PrefixoInfo } from '../../services/api'
import type { ASNDocument } from '../../types/api'
import { sintesePrefixo } from './sintese'

const info = { prefix: '198.18.0.0/24', ip_version: 4, origin_asn: 64496, uf: 'ES', snapshot_date: '2026-09-20', geo_org: { name: 'Provedor 01 Telecom Ltda' } } as PrefixoInfo
const asn = (s: string) => ({ rpki_validation: { '198.18.0.0/24': s } }) as unknown as ASNDocument

describe('síntese do prefixo', () => {
  it('origem, RPKI e geo, cada um com seu selo', () => {
    const f = sintesePrefixo(info, asn('valid'))
    expect(f.map((x) => [x.id, x.selo])).toEqual([['origem', 'fato'], ['rpki', 'fato'], ['geo', 'inferido']])
    expect(f[0].texto).toBe('198.18.0.0/24 é originado pelo AS64496 (Provedor 01 Telecom Ltda) na tabela de roteamento.')
    expect(f[2].texto).toContain('não indica a posição de equipamento nem de pessoa')
  })
  it('estados de RPKI', () => {
    expect(sintesePrefixo(info, asn('invalid'))[1].texto).toContain('inválida')
    expect(sintesePrefixo(info, asn('not_found'))[1].texto).toContain('Nenhum ROA')
  })
  it('sem o AS carregado ou sem origem, não inventa nada', () => {
    expect(sintesePrefixo(info).map((x) => x.id)).toEqual(['origem', 'geo'])
    const sem = sintesePrefixo({ ...info, origin_asn: null, uf: null })
    expect(sem).toHaveLength(1)
    expect(sem[0].texto).toContain('não há origem observada')
  })
})
