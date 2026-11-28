// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { linhasCsv, textoCsv } from './csv'
import { circlePolygon } from './geo'
import { colorByItems, colorByNota, colorExpr, colorValueLabel } from './estilo'

const f = (properties: Record<string, unknown>): GeoJSON.Feature => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [0, 0] }, properties })

describe('CSV das camadas', () => {
  it('sedes de AS: cabeçalho, sim/não/vazio e lista de PTTs', () => {
    const r = linhasCsv([f({ asn: 64500, name: 'Exemplo', city: 'Vitória', uf: 'ES', country: 'BR', has_rpki: true, has_aspa: false, pct_v6: 12.5, ixps_direct: 'sp,rj' }), f({ asn: 1 })], 'asns_geo')!
    expect(r.headers[0]).toBe('asn')
    expect(r.rows[0]).toEqual(['64500', 'Exemplo', 'Vitória', 'ES', 'BR', '', 'sim', 'não', '', '12.5', 'sp,rj'])
    expect(r.rows[1].slice(0, 2)).toEqual(['1', '']) 
    expect(r.rows[1][6]).toBe('')                                    // tem_roa ausente → vazio, não "não"
  })

  it('SCM junta os ASNs com espaço; prefixos e prefixos de PTT têm colunas próprias', () => {
    expect(linhasCsv([f({ cnpj: '1', asns: [10, 20] })], 'outorgas_scm')!.rows[0][5]).toBe('10 20')
    expect(linhasCsv([f({ prefix_count: 7, ip_version: 4, origin_asn: 64500 })], 'prefixes_v4')!.rows[0]).toEqual(['64500', '4', '', '', '', '7'])
    expect(linhasCsv([f({ block_count: 3, block_unit: '/24', origin_asns: [1, 2], peer_asns: [3] })], 'prefixos_ix_v6')!.rows[0].slice(0, 4)).toEqual(['3', '/24', '1 2', '3'])
  })

  it('SCM: sem a coluna situacao (vazia em todos os registros) e com as colunas sici_* do balão', () => {
    const r = linhasCsv([
      f({ cnpj: '1', uf: 'AM', asns: [], sici_ativo: true, sici_mes_referencia: '2026-09', sici_acessos: 1239, sici_pf: 1000, sici_pj: 239, sici_municipios: 3, sici_tecnologia: 'Fibra' }),
      f({ cnpj: '2', sici_ativo: 'false', sici_mes_referencia: '2026-09', sici_acessos: 0 }),
      f({ cnpj: '3' }),
    ], 'outorgas_scm')!
    expect(r.headers).not.toContain('situacao')
    expect(r.headers.slice(5)).toEqual(['asns', 'sici_ativo', 'sici_mes_referencia', 'sici_acessos', 'sici_pf', 'sici_pj', 'sici_municipios', 'sici_tecnologia'])
    expect(r.rows.every((l) => l.length === r.headers.length)).toBe(true)
    expect(r.rows[0].slice(5)).toEqual(['', 'sim', '2026-09', '1239', '1000', '239', '3', 'Fibra'])
    expect(r.rows[1].slice(6, 9)).toEqual(['não', '2026-09', '0'])
    // snapshot antigo: nada é afirmado, nem "não" nem zero
    expect(r.rows[2].slice(6)).toEqual(['', '', '', '', '', '', ''])
  })

  it('camada sem exportação devolve null', () => {
    expect(linhasCsv([f({})], 'pix')).toBeNull()
    expect(linhasCsv([f({})], 'roads_federal')).toBeNull()
  })

  it('texto: BOM, aspas duplicadas e uma linha por registro', () => {
    const t = textoCsv(['a', 'b'], [['x"y', 'z'], ['1', '']])
    expect(t.startsWith('﻿"a","b"\n')).toBe(true)
    expect(t).toContain('"x""y","z"')
    expect(t.split('\n')).toHaveLength(3)
  })
})

describe('círculo de proximidade', () => {
  it('fecha o anel e fica à distância pedida (≈ km) nos pontos cardeais', () => {
    const c = circlePolygon(-46.6, -23.5, 100, 4) as GeoJSON.Feature<GeoJSON.Polygon>
    const anel = c.geometry.coordinates[0]
    expect(anel).toHaveLength(5)
    expect(anel[0]).toEqual([anel[0][0], anel[0][1]])
    expect(anel[0][0]).toBeCloseTo(anel[4][0], 6)
    const norte = anel[1]                                            // t = π/2
    expect((norte[1] - -23.5) * 110.574).toBeCloseTo(100, 0)
  })
})

describe('colorir por', () => {
  it('rótulos do balão e itens da legenda por dimensão', () => {
    expect(colorValueLabel('both', 'visibility')).toBe('IPv6 + IPv4')
    expect(colorValueLabel('v6_only', 'visibility')).toBe('Só IPv6')
    expect(colorValueLabel('yes', 'rpki')).toBe('Com ROA publicada')
    expect(colorValueLabel('no', 'aspa')).toBe('Sem ASPA publicada')
    expect(colorValueLabel('unknown', 'rpki')).toBe('Sem dado')
    expect(colorValueLabel(37, 'pct_v6')).toBe('37% IPv6')
    expect(colorValueLabel('with_scm', 'outorga')).toBe('Com outorga SCM')
    expect(colorValueLabel('x', 'solid')).toBe('')
    expect(colorByItems('porte').map(i => i.label)).toEqual(['Micro empresa', 'Pequeno porte', 'Demais', 'Desconhecido'])
    expect(colorByItems('solid')).toEqual([])
  })

  it('expressão do MapLibre: cor única é literal; as demais casam color_value com um padrão final', () => {
    expect(colorExpr('solid')[0]).toBe('literal')
    expect(colorExpr('qualquer-coisa')[0]).toBe('literal')
    const rpki = colorExpr('rpki') as unknown[]
    expect(rpki.slice(0, 2)).toEqual(['match', ['get', 'color_value']])
    expect(rpki[rpki.length - 1]).toBe('#d9dde3')
    expect(JSON.stringify(colorExpr('pct_v6'))).toContain('interpolate')
  })

  it('ROA, ASPA e ROV: rótulos e itens de legenda do pedido, ROV com faixas em texto', () => {
    expect(colorByItems('rpki').map(i => i.label)).toEqual(['Com ROA publicada', 'Sem ROA publicada', 'Sem dado'])
    expect(colorByItems('aspa').map(i => i.label)).toEqual(['Com ASPA publicada', 'Sem ASPA publicada', 'Sem dado'])
    expect(colorByItems('rov').map(i => i.label)).toEqual(['Até 10% das medições com validação', 'De 10% a 90%', 'Acima de 90%', 'Amostra insuficiente', 'Sem dado'])
    expect(colorValueLabel('acima_de_90', 'rov')).toBe('Acima de 90% das medições com validação')
    expect(colorValueLabel('amostra_insuficiente', 'rov')).toBe('Amostra insuficiente')
    expect(colorValueLabel(undefined, 'rov')).toBe('Sem dado')
  })

  it('notas da legenda: ASPA diz que a verificação não é medida; ROV leva o selo estimado e cita o APNIC', () => {
    expect(colorByNota('aspa')!.nota).toContain('verificação de ASPA')
    expect(colorByNota('aspa')!.nota).toContain('não é medida')
    expect(colorByNota('rov')!.selo).toBe('estimado')
    expect(colorByNota('rov')!.nota).toContain('APNIC')
    expect(colorByNota('porte')).toBeNull()
  })

  it('cor não expressa juízo: sem vermelho nem verde nas dimensões tratadas, em itens e expressões', () => {
    const proibidas = ['#dc2626', '#16a34a', '#f59e0b']
    for (const por of ['rpki', 'aspa', 'rov', 'pct_v6']) {
      const texto = JSON.stringify(colorExpr(por)) + JSON.stringify(colorByItems(por))
      for (const c of proibidas) expect(texto).not.toContain(c)
    }
  })

  it('CSV das sedes: colunas do ROV só quando a consulta trouxe rov_faixa', () => {
    const sem = linhasCsv([f({ asn: 1 })], 'asns_geo')!
    expect(sem.headers).not.toContain('rov_faixa')
    const com = linhasCsv([f({ asn: 1, rov_faixa: 'de_10_a_90', rov_pct: 42.5 }), f({ asn: 2, rov_faixa: 'sem_dado' })], 'asns_geo')!
    expect(com.headers.slice(-2)).toEqual(['rov_faixa', 'rov_pct'])
    expect(com.rows[0].slice(-2)).toEqual(['de_10_a_90', '42.5'])
    expect(com.rows[1].slice(-2)).toEqual(['sem_dado', ''])
  })
})
