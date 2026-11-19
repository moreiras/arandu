// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { agregarCdnBrasil } from './VisaoBrasil'

describe('CDN sob a ótica brasileira', () => {
  it('soma prefixos por PTT do IX.br e família de IP e ignora PTTs fora do IX.br', () => {
    const docs = [
      { asn: 1, ixp_peers: { sp: { v4: { total_prefixes: 10, own_prefixes: 10 }, v6: { total_prefixes: 2, own_prefixes: 2 } }, amsix: { v4: { total_prefixes: 99, own_prefixes: 99 } } }, historico: { completo: true, snapshots_com_historico: 2, colunas: [], eventos: [], eventos_total: 0, serie: [{ date: '2026-11-01', n_ixd: 3 }, { date: '2026-11-08', n_ixd: 4 }] } },
      { asn: 2, ixp_peers: { sp: { v4: { total_prefixes: 5, own_prefixes: 5 } }, rj: { v6: { total_prefixes: 1, own_prefixes: 1 } } }, historico: { completo: true, snapshots_com_historico: 2, colunas: [], eventos: [], eventos_total: 0, serie: [{ date: '2026-11-08', n_ixd: 6 }] } },
    ]
    const r = agregarCdnBrasil(docs as any, ['sp', 'rj'])
    expect(r.linhas).toEqual([{ code: 'sp', v4: 15, v6: 2 }, { code: 'rj', v4: 0, v6: 1 }])
    expect(r.serie).toEqual([['2026-11-01', 3], ['2026-11-08', 6]])
  })
})
