// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { EXEMPLOS, EntradaComparador, entidadeDoCaminho } from './EntradaComparador'
import { idValido } from './entidades'

describe('EntradaComparador', () => {
  it('reconhece a entidade pelo caminho e ignora o resto', () => {
    expect(entidadeDoCaminho('/asn/15169')).toEqual({ tipo: 'asn', id: '15169' })
    expect(entidadeDoCaminho('/ixp/sp?date=2026-11-05')).toEqual({ tipo: 'ixp', id: 'sp' })
    expect(entidadeDoCaminho('/mapa')).toBeNull()
    expect(entidadeDoCaminho('/uf/SP')).toBeNull()
  })
  it('os exemplos usam identificadores válidos de cada tipo, 2 a 4 por comparação', () => {
    for (const x of EXEMPLOS) {
      expect(x.ids.length).toBeGreaterThanOrEqual(2)
      if (x.tipo !== 'ixp') for (const id of x.ids) expect(idValido(x.tipo, id), `${x.tipo} ${id}`).toBe(id)
    }
  })
  it('mostra um exemplo por tipo e os recentes como começo de comparação', () => {
    render(<MemoryRouter><EntradaComparador recentes={[{ titulo: 'AS64500', detalhe: 'x', url: '/asn/64500' }, { titulo: 'Mapa', detalhe: '', url: '/mapa' }]} /></MemoryRouter>)
    expect(screen.getAllByRole('link').filter((a) => a.getAttribute('href')?.startsWith('/comparar?tipo=')).length).toBe(EXEMPLOS.length + 1)
    expect(screen.getByRole('link', { name: /AS: AS64500|ASe?: AS64500/ })).toHaveAttribute('href', '/comparar?tipo=asn&ids=64500')
    expect(screen.queryByText('Mapa')).toBeNull()
  })
})

describe('comparador de grupos', () => {
  it('aceita grp_ e ind_ como identificador e rejeita o resto', async () => {
    const { idValido, compararGrupos } = await import('./entidades')
    expect(idValido('grupo', 'grp_66970229')).toBe('grp_66970229')
    expect(idValido('grupo', 'IND_02558157')).toBe('ind_02558157')
    expect(idValido('grupo', '66970229')).toBeNull()
    expect(idValido('grupo', "grp_'; drop")).toBeNull()
    const g = (id: string, ac: number, pos: number | null) => ({
      grupo: { grupo_id: id, tamanho: 1, empresas: 1, classificacao: 'individual', assinantes: ac, usuarios_apnic: 10, cnpjs: [{ empresa: 'Empresa ' + id }], municipios: [], asns: [] } as never,
      mercado: pos ? { cnpjs_com_acessos: 1, cnpjs_total: 1, serie: [{ mes: '2026-09', acessos: ac, parcela: 1.5 }], posicao: { atual: pos, ha_12_meses: null, mes_ha_12_meses: null, unidades: 100 }, por_uf: [] } as never : null,
      regulatorio: null, tecnico: null,
    })
    const c = compararGrupos([g('ind_1', 100, 2), g('ind_2', 50, null)])
    expect(c.colunas.map((x) => x.to)).toEqual(['/grupo/ind_1', '/grupo/ind_2'])
    expect(c.linhas.find((l) => l.id === 'posicao')!.celulas).toEqual(['2º de 100', null])
    expect(c.linhas.find((l) => l.id === 'composicao')!.selo).toBe('inferido')
    expect(c.linhas.map((l) => l.id)).not.toContain('multas')                      // sem comparar multa ou reclamação entre grupos
  })
})
