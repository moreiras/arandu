// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import type { ASNDocument, ReferenciasAsn } from '../../types/api'
import { fraseTransito, kpisAs, provedoresTransitoV4, REGRAS_VERSAO, sinteseAs } from './sintese'

const base = {
  asn: 64496, name: 'Provedor 01 Telecom Ltda', is_br: true, global_prefixes_v4_count: 3, global_prefixes_v6_count: 1, global_prefixes_v4: ['a', 'b', 'c'], global_prefixes_v6: ['d'],
  ixps_direct: ['sp', 'rj'], ixps_origin: ['sp', 'rj', 'mg'], rpki_validation: { a: 'valid', b: 'valid', c: 'not_found', d: 'invalid' },
  apnic_users: 3068, apnic_v6_pct_as: 20, alerts: [],
} as unknown as ASNDocument
const ref: ReferenciasAsn = { universo: 'x', total: 1136, usuarios_posicao: 12, usuarios_com_dado: 900, pct_v6_mediana: 8.5, prefixos_v4_mediana: 2, ixps_diretos_mediana: 1 }
const ids = (d: ASNDocument, r?: ReferenciasAsn) => sinteseAs(d, r).map((f) => f.id)

describe('frase-síntese do AS (regras versionadas)', () => {
  it('tem versão das regras', () => expect(REGRAS_VERSAO).toBe('sintese-as-3'))

  it('AS completo: anúncio, PTTs, RPKI, usuários com posição; cada frase com selo', () => {
    const f = sinteseAs(base, ref)
    expect(f.map((x) => x.id)).toEqual(['anuncio', 'ptts', 'rpki', 'usuarios', 'transito'])
    expect(f[0].texto).toBe('AS64496 (Provedor 01 Telecom Ltda) anuncia 1 prefixo IPv6 e 3 prefixos IPv4 na tabela de roteamento global.')
    expect(f[1].texto).toBe('AS64496 tem sessão direta em 2 PTTs do IX.br e aparece como originador em 3 PTTs.')
    expect(f[2].texto).toBe('2 de 4 prefixos anunciados têm ROA válido, e 1 está inválido.')
    expect(f[3]).toMatchObject({ selo: 'estimado', texto: 'O APNIC estima cerca de 3.068 usuários neste AS, que ocupa o 12º lugar entre os 900 ASes brasileiros com estimativa.' })
    expect(f.filter((x) => !['usuarios', 'transito'].includes(x.id)).every((x) => x.selo === 'fato')).toBe(true)
  })

  it('sem referência do servidor, a frase de usuários não inventa posição', () => {
    expect(sinteseAs(base).find((f) => f.id === 'usuarios')!.texto).toBe('O APNIC estima cerca de 3.068 usuários neste AS.')
  })

  it('regra sem dado não gera frase (nada de palpite)', () => {
    const vazio = { ...base, global_prefixes_v4_count: 0, global_prefixes_v6_count: 0, ixps_direct: [], ixps_origin: [], rpki_validation: {}, apnic_users: null } as unknown as ASNDocument
    const f = sinteseAs(vazio)
    expect(f.map((x) => x.id)).toEqual(['anuncio', 'ptts', 'transito'])
    expect(f[2].texto).toBe('Este snapshot não traz inferência de provedores de trânsito.')
    expect(f[0].texto).toContain('não aparece com prefixos')
    expect(f[1].texto).toContain('não aparece em PTTs')
  })

  it('trânsito sai das relações (ARC), nunca dos campos deprecados de adjacência', () => {
    const f = sinteseAs({ ...base, single_upstream_v4: 64500, is_multihomed_v4: true, upstreams_v4: [64496, 64500] } as ASNDocument)
    expect(f.find((x) => x.id === 'transito')).toMatchObject({ selo: 'inferido', texto: 'Este snapshot não traz inferência de provedores de trânsito.' })
    expect(ids(base)).toContain('transito')
  })

  const rel = (provedores: Array<[number, string]>, extra: object = {}) => ({
    algoritmo: 'ARC v2', provedores: provedores.map(([asn, nivel]) => ({ asn, nivel, p: 0.9, afi: ['v4'] })), clientes: [], pares: [], irmaos: [], sem_classificacao: [],
    n_provedores: { v4: 0, v6: 0 }, visibilidade: { v4: { vps: 5, ptts: 1, coletores: true }, v6: { vps: 0, ptts: 0, coletores: true } },
    multihomed: { v4: true, v6: null }, single_homed: { v4: false, v6: null }, ...extra,
  })

  it('ASN-E4: AS13357 com 2 prováveis e 4 possíveis; o irmão do mesmo CNPJ fica de fora', () => {
    const d = { ...base, asn: 13357, same_cnpj_asns: [{ asn: 28158, name: 'Irmã' }],
      relacoes: rel([[174, 'provavel'], [3356, 'provavel'], [28158, 'provavel'], [14840, 'possivel'], [6057, 'possivel'], [137409, 'possivel'], [35280, 'possivel']]) } as unknown as ASNDocument
    expect(provedoresTransitoV4(d)).toMatchObject({ fortes: [174, 3356], possiveis: [14840, 6057, 137409, 35280], irmaos: [28158] })
    expect(fraseTransito(d)).toBe('Pelas relações inferidas, o AS tem 2 provedores de trânsito IPv4 de nível provável ou superior (AS174, AS3356), além de 4 de nível possível. AS28158, do mesmo CNPJ ou da mesma organização, não entra na contagem.')
  })

  it('nunca conta o próprio AS; só possíveis não vira multihoming; multihomed nulo sem relação é visibilidade insuficiente', () => {
    const proprio = { ...base, asn: 28573, relacoes: rel([[28573, 'provavel']], { multihomed: { v4: null, v6: null } }) } as unknown as ASNDocument
    expect(fraseTransito(proprio)).toBe('Não há visibilidade suficiente para inferir provedores de trânsito IPv4.')
    const so = { ...base, relacoes: rel([[1, 'possivel'], [2, 'possivel']], { multihomed: { v4: null, v6: null } }) } as unknown as ASNDocument
    expect(fraseTransito(so)).toBe('Pelas relações inferidas, nenhum provedor de trânsito IPv4 chega ao nível provável neste snapshot; há 2 relações possíveis.')
    expect(fraseTransito(so)).not.toMatch(/mais de um provedor/)
    const um = { ...base, relacoes: rel([[3356, 'confirmado']], { multihomed: { v4: false, v6: null } }) } as unknown as ASNDocument
    expect(fraseTransito(um)).toBe('Pelas relações inferidas, o AS tem um provedor de trânsito IPv4 de nível provável ou superior (AS3356).')
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
