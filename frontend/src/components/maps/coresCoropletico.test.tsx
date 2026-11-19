// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { INDICADORES_MUNICIPAIS, formatarValor, indicadorPorId } from '../../lib/indicadoresMapa'
import { COR_SEM_DADO, PALETA_BIVARIADA, classeBivariada, coresDasClasses, expressaoBivariada, expressaoCor } from './coresCoropletico'
import { LegendaBivariada, LegendaQuebras } from './LegendaQuebras'
import { PequenosMultiplos } from './PequenosMultiplos'

describe('expressão de cor do coroplético', () => {
  const valores = { '1100015': 10, '1100023': 50, '1100031': 90, '1100049': null, '1100056': 55 }
  it('agrupa os códigos por classe e pinta quem não tem dado de cinza', () => {
    const cores = ['#a', '#b', '#c']
    const e = expressaoCor(valores, [40, 80], cores) as unknown[]
    expect(e[0]).toBe('match')
    expect(e[1]).toEqual(['get', 'ibge'])
    expect(e.slice(2, -1)).toEqual([['1100015'], '#a', ['1100023', '1100056'], '#b', ['1100031'], '#c'])
    expect(e[e.length - 1]).toBe(COR_SEM_DADO)
  })
  it('nulo nunca vira zero: não entra em nenhuma classe', () => {
    const e = JSON.stringify(expressaoCor(valores, [40, 80], ['#a', '#b', '#c']))
    expect(e).not.toContain('1100049')
  })
  it('sem nenhum valor devolve só a cor de "sem dado"', () => {
    expect(expressaoCor({}, [], ['#a'])).toBe(COR_SEM_DADO)
  })
  it('cores das classes saem da escala segura (Viridis): primeira escura, última clara', () => {
    const c = coresDasClasses(5)
    expect(c).toHaveLength(5)
    expect(c[0]).toBe('#440154')
    expect(c[4]).toBe('#fde725')
    expect(new Set(c).size).toBe(5)
  })
})

describe('bivariado', () => {
  it('9 cores, classe = linha × 3 + coluna', () => {
    expect(PALETA_BIVARIADA.flat()).toHaveLength(9)
    expect(new Set(PALETA_BIVARIADA.flat()).size).toBe(9)
    expect(classeBivariada(0, 0)).toBe(0)
    expect(classeBivariada(2, 0)).toBe(2)
    expect(classeBivariada(0, 2)).toBe(6)
    expect(classeBivariada(2, 2)).toBe(8)
  })
  it('só pinta quem tem os dois valores', () => {
    const e = expressaoBivariada({ a: 1, b: 50, c: 99 }, { a: 1, b: null, c: 99 }, [30, 60], [30, 60]) as unknown[]
    expect(e.slice(2, -1)).toEqual([['a'], PALETA_BIVARIADA[0][0], ['c'], PALETA_BIVARIADA[2][2]])
    expect(JSON.stringify(e)).not.toContain('"b"')
  })
})

describe('indicadores de mapa: normalização obrigatória', () => {
  it('todo indicador declara o denominador, a unidade e as fontes', () => {
    expect(INDICADORES_MUNICIPAIS.length).toBeGreaterThanOrEqual(4)
    for (const i of INDICADORES_MUNICIPAIS) {
      expect(i.normalizacao.length, i.id).toBeGreaterThan(20)
      expect(i.normalizacao, i.id).toMatch(/÷|distância/)
      expect(i.unidade, i.id).not.toBe('')
      expect(i.fontes.length, i.id).toBeGreaterThan(0)
      expect(i.classes, i.id).toBeGreaterThanOrEqual(3)
    }
    expect(new Set(INDICADORES_MUNICIPAIS.map((i) => i.id)).size).toBe(INDICADORES_MUNICIPAIS.length)
  })
  it('nenhum indicador é um valor absoluto (acessos, população, domicílios) sem denominador', () => {
    for (const i of INDICADORES_MUNICIPAIS) expect(['acessos', 'populacao', 'domicilios']).not.toContain(i.id)
  })
  it('formata em pt-BR com as casas do indicador', () => {
    expect(formatarValor(1234.5, indicadorPorId('km_ptt')!)).toBe('1.235')
  })
})

describe('legendas', () => {
  it('legenda de quebras: uma linha por classe, "sem dado" e o método declarado', () => {
    render(<LegendaQuebras titulo="Acessos por 100 domicílios" unidade="acessos por 100 domicílios" rotulos={['menos de 10', '10 a 20', '20 ou mais']} cores={['#1', '#2', '#3']} metodo="quantis" />)
    const lg = screen.getByTestId('legenda')
    expect(within(lg).getAllByRole('listitem')).toHaveLength(4)
    expect(lg).toHaveTextContent('sem dado')
    expect(lg).toHaveTextContent('mesmo número de municípios')
  })
  it('legenda bivariada: 9 células com a leitura em palavras', () => {
    render(<LegendaBivariada rotuloX="Penetração" rotuloY="Distância ao PTT" />)
    const cel = screen.getAllByRole('cell')
    expect(cel).toHaveLength(9)
    expect(cel[0]).toHaveAttribute('title', 'Penetração: baixo · Distância ao PTT: alto')
    expect(screen.getByTestId('legenda-bivariada')).toHaveTextContent('sem dado em qualquer um dos dois fica cinza')
  })
})

describe('pequenos múltiplos', () => {
  const ufs = [
    { uf: 'SP', ptts: 3, municipios: 600, acessos: 9e6, fibra_pct: 70, asns: 900, usuarios: 3e7, municipios_sem_ptt: 30, domicilios: 1.6e7, penetracao: 0.8 },
    { uf: 'AM', ptts: 0, municipios: 60, acessos: 4e5, fibra_pct: 30, asns: 20, usuarios: 1e6, municipios_sem_ptt: 40, domicilios: 1e6, penetracao: 0.4 },
  ]
  it('um cartograma por indicador normalizado, cada um com o intervalo', () => {
    render(<MemoryRouter><PequenosMultiplos ufs={ufs} metricas={['penetracao', 'fibra', 'longe']} /></MemoryRouter>)
    expect(screen.getAllByTestId('cartograma')).toHaveLength(3)
    expect(screen.getByText('Acessos por 100 domicílios')).toBeInTheDocument()
    expect(screen.getByText('de 40 a 80')).toBeInTheDocument()
  })
})
