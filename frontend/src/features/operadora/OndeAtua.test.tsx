// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** "Onde atua" da operadora (PT-23 / OPERADORA 5.3): resumo por UF que fecha com o total, tabela com parcela, declarantes e HHI local, borda de 1 município e de parcela nula. */
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { OndeAtua } from './OndeAtua'
import { comMaisDaMetade, comUmSoDeclarante, resumoPorUf, type MunicipioOperadora } from './resumoOndeAtua'

const mun = (ibge: string, nome: string, uf: string, acessos: number, o: Partial<MunicipioOperadora> = {}): MunicipioOperadora => ({
  ibge, nome, uf, acessos, pf: acessos - 10, pj: 10, capacidade_mbps: 0, municipio_acessos: acessos * 2, share: 50, municipio_operadores: 96, municipio_hhi: 2750, avisos_hhi: [], ...o,
})
const base = [
  mun('2507507', 'João Pessoa', 'PB', 140638, { share: 45.79, municipio_operadores: 96, municipio_hhi: 2750 }),
  mun('2304400', 'Fortaleza', 'CE', 300000, { share: 21.3, municipio_operadores: 326, municipio_hhi: 1123 }),
  mun('2300101', 'Abaiara', 'CE', 230263, { share: 100, municipio_operadores: 1, municipio_hhi: 10000, avisos_hhi: ['poucos_casos'] }),
  mun('4300000', 'Sem Índice', 'RS', 4, { share: null, municipio_operadores: null, municipio_hhi: null, municipio_acessos: null, avisos_hhi: null }),
]
const montar = (m: MunicipioOperadora[]) => render(<MemoryRouter><OndeAtua municipios={m} mesReferencia="2026-09" snapshot="2026-11-22" /></MemoryRouter>)

describe('resumo por UF', () => {
  it('a soma por UF é o total dos municípios e a ordem é por acessos', () => {
    const r = resumoPorUf(base)
    expect(r.map((u) => u.uf)).toEqual(['CE', 'PB', 'RS'])
    expect(r.reduce((s, u) => s + u.acessos, 0)).toBe(base.reduce((s, m) => s + m.acessos, 0))
    expect(r[0]).toMatchObject({ uf: 'CE', municipios: 2, acessos: 530263 })
    expect(r.reduce((s, u) => s + (u.pct ?? 0), 0)).toBeCloseTo(100, 5)
  })
  it('conta parcela acima de 50% e um só declarante; parcela nula não conta', () => {
    expect(comMaisDaMetade(base)).toBe(1)
    expect(comMaisDaMetade([mun('1', 'A', 'SP', 1, { share: 50 })])).toBe(0)
    expect(comUmSoDeclarante(base)).toBe(1)
  })
})

describe('OndeAtua', () => {
  it('mostra mês do SICI e snapshot, a síntese e o resumo por UF com legenda', () => {
    montar(base)
    expect(screen.getByRole('heading', { name: /Onde atua \(SICI 2026-09 · snapshot 2026-11-22\)/ })).toBeTruthy()
    expect(screen.getByTestId('onde-atua').textContent).toMatch(/4<\/strong>|4 municípios|municípios de/)
    const uf = screen.getByTestId('onde-atua-uf')
    expect(within(uf).getByText('Acessos declarados por UF')).toBeTruthy()
    expect(within(uf).getAllByRole('row').length).toBe(1 + 3 + 1)                  // cabeçalho, três UFs, total
    expect(within(uf).getByText('530.263')).toBeTruthy()
  })

  it('a tabela de municípios tem legenda, escopo, parcela, declarantes e HHI com a faixa em texto', () => {
    montar(base)
    const t = screen.getAllByRole('table')[1]
    expect(t.querySelector('caption')?.textContent).toMatch(/parcela dela nos acessos do município/)
    expect(t.querySelectorAll('thead th[scope="col"]').length).toBe(8)
    const jp = screen.getByRole('link', { name: 'João Pessoa' }).closest('tr')!
    expect(jp.textContent).toContain('45,8%')
    expect(jp.textContent).toContain('2.750')
    expect(jp.textContent).toContain('HHI de 2.500 ou mais')
    expect(jp.textContent).toContain('96')
    const abaiara = screen.getByRole('link', { name: 'Abaiara' }).closest('tr')!
    expect(abaiara.textContent).toContain('10.000')
    expect(abaiara.textContent).toContain('poucos casos')                           // aviso de recorte: só rótulo, a linha continua
  })

  it('parcela e HHI nulos aparecem como "—", nunca como zero', () => {
    montar(base)
    const linha = screen.getByRole('link', { name: 'Sem Índice' }).closest('tr')!
    const celulas = within(linha).getAllByRole('cell').map((c) => c.textContent)
    expect(celulas.slice(-3)).toEqual(['—', '—', '—'])
    expect(linha.textContent).not.toMatch(/0,0%|\b0\b.*HHI/)
  })

  it('filtra por UF e por nome sem acento, e informa o intervalo em região viva', () => {
    montar(base)
    fireEvent.change(screen.getByLabelText('UF'), { target: { value: 'CE' } })
    expect(screen.getByRole('status').textContent).toMatch(/Mostrando 1 a 2 de 2 municípios/)
    fireEvent.change(screen.getByLabelText('Buscar município'), { target: { value: 'joao' } })
    expect(screen.getByRole('status').textContent).toMatch(/Nenhum município com estes filtros/)
    fireEvent.change(screen.getByLabelText('UF'), { target: { value: '' } })
    expect(screen.getByRole('status').textContent).toMatch(/Mostrando 1 a 1 de 1 municípios/)
  })

  it('ordena pela coluna com aria-sort', () => {
    montar(base)
    const cab = screen.getByRole('columnheader', { name: /Parcela no município/ })
    fireEvent.click(within(cab).getByRole('button'))
    expect(cab.getAttribute('aria-sort')).toBe('descending')
    const nomes = within(screen.getAllByRole('table')[1]).getAllByRole('row').slice(1).map((r) => r.querySelector('a')?.textContent)
    expect(nomes).toEqual(['Abaiara', 'João Pessoa', 'Fortaleza', 'Sem Índice'])          // parcela nula vai ao fim
  })

  it('pagina de 100 em 100 sem suprimir linha', () => {
    const muitos = Array.from({ length: 250 }, (_, i) => mun(String(1000 + i), `Cidade ${String(i).padStart(3, '0')}`, 'SP', 1000 - i))
    montar(muitos)
    expect(screen.getByRole('status').textContent).toMatch(/Mostrando 1 a 100 de 250/)
    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }))
    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }))
    expect(screen.getByRole('status').textContent).toMatch(/Mostrando 201 a 250 de 250/)
    expect(screen.getByRole('button', { name: 'Próxima' })).toHaveProperty('disabled', true)
  })

  it('com um só município mostra só a frase', () => {
    montar([base[0]])
    expect(screen.queryAllByRole('table').length).toBe(0)
    expect(screen.getByTestId('onde-atua').textContent).toMatch(/Declara acessos em um município: João Pessoa\/PB, com 140\.638 acessos \(45,8% dos acessos declarados no município, 96 declarantes, HHI local 2\.750\)/)
  })

  it('sem municípios não desenha nada', () => {
    const { container } = montar([])
    expect(container.textContent).toBe('')
  })

  it('traz a nota das faixas como método do projeto, sem juízo de valor', () => {
    montar(base)
    const txt = screen.getByTestId('onde-atua').textContent ?? ''
    expect(txt).toMatch(/Faixas de HHI adotadas pelo OBINT \(método do projeto\)/)
    expect(txt).toMatch(/A sede do CNPJ não indica onde estão os clientes/)
    expect(txt).not.toMatch(/domínio|monopólio|abuso|omitiu/i)
  })
})
