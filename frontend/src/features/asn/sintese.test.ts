// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import type { ASNDocument, ReferenciasAsn } from '../../types/api'
import { kpisAs, REGRAS_VERSAO, sinteseAs } from './sintese'

const base = {
  asn: 64496, name: 'Provedor 01 Telecom Ltda', is_br: true, global_prefixes_v4_count: 3, global_prefixes_v6_count: 1, global_prefixes_v4: ['a', 'b', 'c'], global_prefixes_v6: ['d'],
  ixps_direct: ['sp', 'rj'], ixps_origin: ['sp', 'rj', 'mg'], rpki_validation: { a: 'valid', b: 'valid', c: 'not_found', d: 'invalid' },
  apnic_users: 3068, apnic_v6_pct_as: 20, alerts: [],
} as unknown as ASNDocument
const ref: ReferenciasAsn = { universo: 'x', total: 1136, usuarios_posicao: 12, usuarios_com_dado: 900, pct_v6_mediana: 8.5, prefixos_v4_mediana: 2, ixps_diretos_mediana: 1 }
const ids = (d: ASNDocument, r?: ReferenciasAsn) => sinteseAs(d, r).map((f) => f.id)

describe('frase-síntese do AS (regras versionadas)', () => {
  it('tem versão das regras', () => expect(REGRAS_VERSAO).toBe('sintese-as-1'))

  it('AS completo: anúncio, PTTs, RPKI, usuários com posição; cada frase com selo', () => {
    const f = sinteseAs(base, ref)
    expect(f.map((x) => x.id)).toEqual(['anuncio', 'ptts', 'rpki', 'usuarios'])
    expect(f[0].texto).toBe('AS64496 (Provedor 01 Telecom Ltda) anuncia 1 prefixo IPv6 e 3 prefixos IPv4 na tabela de roteamento global.')
    expect(f[1].texto).toBe('Está em 2 PTTs do IX.br com sessão direta e aparece como originador em 3 PTTs.')
    expect(f[2].texto).toBe('2 de 4 prefixos anunciados têm ROA válido; 1 está inválido.')
    expect(f[3]).toMatchObject({ selo: 'estimado', texto: 'Estimativa do APNIC: cerca de 3.068 usuários (12º entre 900 ASes brasileiros com estimativa).' })
    expect(f.filter((x) => x.id !== 'usuarios').every((x) => x.selo === 'fato')).toBe(true)
  })

  it('sem referência do servidor, a frase de usuários não inventa posição', () => {
    expect(sinteseAs(base).find((f) => f.id === 'usuarios')!.texto).toBe('Estimativa do APNIC: cerca de 3.068 usuários.')
  })

  it('regra sem dado não gera frase (nada de palpite)', () => {
    const vazio = { ...base, global_prefixes_v4_count: 0, global_prefixes_v6_count: 0, ixps_direct: [], ixps_origin: [], rpki_validation: {}, apnic_users: null } as unknown as ASNDocument
    const f = sinteseAs(vazio)
    expect(f.map((x) => x.id)).toEqual(['anuncio', 'ptts'])
    expect(f[0].texto).toContain('não aparece com prefixos')
    expect(f[1].texto).toContain('Não aparece em PTTs')
  })

  it('trânsito é inferência e só aparece com o dado do grafo', () => {
    expect(ids(base)).not.toContain('transito')
    const f = sinteseAs({ ...base, single_upstream_v4: 64500 } as ASNDocument)
    expect(f.find((x) => x.id === 'transito')).toMatchObject({ selo: 'inferido', texto: expect.stringContaining('único provedor de trânsito IPv4 (AS64500)') })
    expect(sinteseAs({ ...base, is_multihomed_v4: true } as ASNDocument).find((x) => x.id === 'transito')!.texto).toContain('mais de um provedor')
  })

  it('singular e plural: 1 prefixo, 1 de 1 prefixo anunciado tem ROA', () => {
    const um = { ...base, global_prefixes_v4_count: 1, global_prefixes_v6_count: 0, rpki_validation: { a: 'valid' }, alerts: [{}, {}] } as unknown as ASNDocument
    const f = sinteseAs(um)
    expect(f[0].texto).toContain('0 prefixos IPv6 e 1 prefixo IPv4')
    expect(f.find((x) => x.id === 'rpki')!.texto).toBe('1 de 1 prefixo anunciado tem ROA válido.')
    expect(f.find((x) => x.id === 'alertas')!.texto).toContain('2 pontos de atenção')
  })

  it('indicadores com referência: posição e medianas; sem referência, sem texto de comparação', () => {
    const k = Object.fromEntries(kpisAs(base, ref).map((x) => [x.id, x]))
    expect(k.usuarios.referencia).toBe('12º de 900 ASes BR')
    expect(k.v4.referencia).toBe('mediana dos ASes BR: 2')
    expect(k.v6usuarios.referencia).toBe('mediana dos ASes BR: 8,5%')
    expect(kpisAs(base).every((x) => x.referencia === undefined)).toBe(true)
  })
})
