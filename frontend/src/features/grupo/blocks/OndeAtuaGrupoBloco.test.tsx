// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** "Onde o conjunto atua" do grupo (PT-23 / GRUPO 5.4): tabela municipal com parcela, declarantes e HHI por grupo (inferido) e por CNPJ, prévia de 100 linhas e estados de borda. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { server } from '../../../test/server'
import type { GrupoMunicipioLinha, GrupoMunicipios } from '../../../types/api'
import { OndeAtuaGrupoBloco } from './OndeAtuaGrupoBloco'

const linha = (ibge: string, nome: string, uf: string, acessos: number, o: Partial<GrupoMunicipioLinha> = {}): GrupoMunicipioLinha => ({
  ibge, nome, uf, acessos, cnpjs_do_conjunto: 2, municipio_acessos: acessos * 2, parcela: 50, declarantes: 12, hhi_grupo: 2169, faixa_grupo: 'moderado', avisos_grupo: [], hhi_cnpj: 1758, faixa_cnpj: 'moderado', ...o,
})
const resposta = (items: GrupoMunicipioLinha[], o: Partial<GrupoMunicipios> = {}): GrupoMunicipios => ({
  snapshot_date: '2026-11-22', grupo_id: 'grp_09132659', mes_referencia: '2026-09', tamanho: 3, natureza: 'fato com agrupamento inferido', limites: 'Acessos fixos declarados pelas empresas à Anatel.',
  resumo: { municipios: items.length, com_mais_da_metade: 1, com_um_so_declarante: 1, acessos: items.reduce((s, l) => s + l.acessos, 0), ufs: 1 }, filtros: { uf: null, q: null }, ordem: 'acessos do conjunto no município (decrescente)',
  page: 1, limit: 100, total: items.length, items, ...o,
})
const grupo = (extra: object = {}) => ({ dados: { grupo: { grupo_id: 'grp_09132659', municipios: [{ ibge: '1', uf: 'SE' }, { ibge: '2', uf: 'BA' }], ...extra } } as never, snapshot: '2026-11-22' })

const pedidos: URL[] = []
const ultimo = () => pedidos[pedidos.length - 1]
function montar(corpo: GrupoMunicipios | ((u: URL) => GrupoMunicipios), g = grupo()) {
  pedidos.length = 0
  server.use(http.get('*/api/v1/grupos/grp_09132659/municipios', ({ request }) => { const u = new URL(request.url); pedidos.push(u); return HttpResponse.json(typeof corpo === 'function' ? corpo(u) : corpo) }))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={['/grupo/grp_09132659?date=2026-11-22']}><OndeAtuaGrupoBloco {...g} /></MemoryRouter></QueryClientProvider>)
}

describe('Onde o conjunto atua (grupo)', () => {
  it('síntese com mês do SICI, tabela com legenda e as duas leituras de HHI', async () => {
    montar(resposta([linha('1', 'Aracaju', 'SE', 3002, { parcela: 61.2, declarantes: 8, hhi_grupo: 3900, faixa_grupo: 'concentrado' }), linha('2', 'Indiaroba', 'SE', 1478, { parcela: 100, declarantes: 1, hhi_grupo: 10000, hhi_cnpj: 10000, faixa_grupo: 'concentrado', faixa_cnpj: 'concentrado' })]))
    const t = await screen.findByTestId('grupo-onde-atua-tabela')
    expect(t.querySelector('caption')?.textContent).toMatch(/parcela do conjunto nos acessos do município/)
    expect(screen.getByTestId('grupo-onde-atua').textContent).toMatch(/Em 1 deles tem mais da metade dos acessos declarados no município e em 1 é a única empresa declarante \(SICI 2026-09\)/)
    const cab = within(t).getAllByRole('columnheader').map((c) => c.textContent)
    expect(cab.join('|')).toMatch(/HHI local por grupo \(inferido\)/)
    expect(cab.join('|')).toMatch(/HHI local por CNPJ/)
    const ar = within(t).getByRole('link', { name: 'Aracaju' }).closest('tr')!
    expect(ar.textContent).toContain('3.002')
    expect(ar.textContent).toContain('61,2%')
    expect(ar.textContent).toContain('3.900')
    expect(ar.textContent).toContain('2 CNPJs')
    expect(within(t).getByRole('link', { name: 'Indiaroba' }).closest('tr')!.textContent).toContain('1 (uma só empresa declarante)')
    expect(screen.getByTestId('grupo-onde-atua').textContent).toMatch(/Faixas de HHI adotadas pelo OBINT \(método do projeto\)/)
  })

  it('pede a primeira página de 100 em ordem de acessos; clicar na coluna pede a ordem ao servidor', async () => {
    montar(resposta([linha('1', 'Aracaju', 'SE', 3002)]))
    await screen.findByTestId('grupo-onde-atua-tabela')
    expect(pedidos[0].searchParams.get('limit')).toBe('100')
    expect(pedidos[0].searchParams.get('ordem')).toBe('acessos')
    expect(pedidos[0].searchParams.get('desc')).toBe('true')
    expect(pedidos[0].searchParams.get('esquema')).toBe('6')
    fireEvent.click(within(screen.getByRole('columnheader', { name: /Município/ })).getByRole('button'))
    await waitFor(() => expect(ultimo().searchParams.get('ordem')).toBe('nome'))
    expect(ultimo().searchParams.get('desc')).toBe('false')
  })

  it('filtro de UF e busca vão ao servidor e voltam à página 1', async () => {
    montar(resposta([linha('1', 'Aracaju', 'SE', 3002)]))
    await screen.findByTestId('grupo-onde-atua-tabela')
    fireEvent.change(screen.getByLabelText('UF'), { target: { value: 'SE' } })
    await waitFor(() => expect(ultimo().searchParams.get('uf')).toBe('SE'))
    fireEvent.change(screen.getByLabelText('Buscar município'), { target: { value: 'araj' } })
    await waitFor(() => expect(ultimo().searchParams.get('q')).toBe('araj'))
    expect(ultimo().searchParams.get('page')).toBe('1')
  })

  it('anônimo vê a prévia de 100 de N, sem erro e sem lista vazia', async () => {
    const cem = Array.from({ length: 100 }, (_, i) => linha(String(i), `Cidade ${i}`, 'SE', 1000 - i))
    montar(resposta(cem, { total: 5443, resumo: { municipios: 5443, com_mais_da_metade: 10, com_um_so_declarante: 2, acessos: 9, ufs: 27 } }))
    expect((await screen.findByTestId('previa-lista')).textContent).toBe('Prévia: 100 de 5.443. Entre para ver as demais.')
    expect(screen.getByText(/de 55 páginas|página 1 de 55/)).toBeTruthy()
  })

  it('grupo individual (um CNPJ ou S.A.) mostra uma só coluna de HHI e o rótulo de S.A. quando não inferível', async () => {
    montar(resposta([linha('1', 'Aracaju', 'SE', 3002, { hhi_grupo: 1758, hhi_cnpj: 1758, cnpjs_do_conjunto: 1 })], { tamanho: 1, grupo_inferivel: false }))
    const t = await screen.findByTestId('grupo-onde-atua-tabela')
    const cab = within(t).getAllByRole('columnheader').map((c) => c.textContent).join('|')
    expect(cab).toMatch(/HHI local/)
    expect(cab).not.toMatch(/por grupo|por CNPJ/)
    expect(screen.getByTestId('grupo-nao-inferivel')).toBeTruthy()
  })

  it('sem municípios no grupo diz o fato, sem pedir a tabela', () => {
    montar(resposta([]), grupo({ municipios: [] }))
    expect(screen.getByText(/Nenhuma empresa do grupo declarou acessos fixos ao SICI/)).toBeTruthy()
    expect(pedidos.length).toBe(0)
  })

  it('filtro sem resultado informa e mantém os controles', async () => {
    montar(resposta([], { total: 0, resumo: { municipios: 2, com_mais_da_metade: 0, com_um_so_declarante: 0, acessos: 0, ufs: 0 } }))
    expect(await screen.findByText(/Nenhum município com estes filtros/)).toBeTruthy()
    expect(screen.getByLabelText('Buscar município')).toBeTruthy()
  })
})
