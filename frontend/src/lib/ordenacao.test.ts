// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { alternarOrdem, ordenar, useOrdenacao } from './ordenacao'

const linhas = [
  { nome: 'Ébano', n: 3 },
  { nome: 'abacate', n: null },
  { nome: 'Zebra', n: 10 },
  { nome: 'banana', n: 2 },
]

describe('ordenar', () => {
  it('vazios ficam no fim nos dois sentidos e textos seguem o pt-BR', () => {
    expect(ordenar(linhas, (l) => l.n, 'desc').map((l) => l.n)).toEqual([10, 3, 2, null])
    expect(ordenar(linhas, (l) => l.n, 'asc').map((l) => l.n)).toEqual([2, 3, 10, null])
    expect(ordenar(linhas, (l) => l.nome, 'asc').map((l) => l.nome)).toEqual(['abacate', 'banana', 'Ébano', 'Zebra'])
  })
})

describe('alternarOrdem', () => {
  it('outra coluna começa no sentido dado; a mesma inverte', () => {
    expect(alternarOrdem(null, 'a')).toEqual({ campo: 'a', dir: 'desc' })
    expect(alternarOrdem({ campo: 'a', dir: 'desc' }, 'a')).toEqual({ campo: 'a', dir: 'asc' })
    expect(alternarOrdem({ campo: 'a', dir: 'asc' }, 'b', 'asc')).toEqual({ campo: 'b', dir: 'asc' })
  })
})

describe('useOrdenacao', () => {
  it('ordena a lista inteira antes do corte: o maior da coluna aparece no top 2 mesmo fora das 2 primeiras linhas', () => {
    const { result } = renderHook(() => useOrdenacao(linhas, { nome: (l) => l.nome, n: (l) => l.n }))
    expect(result.current.ordenados.slice(0, 2).map((l) => l.nome)).toEqual(['Ébano', 'abacate'])
    act(() => result.current.alternar('n'))
    expect(result.current.ordem).toEqual({ campo: 'n', dir: 'desc' })
    expect(result.current.ordenados.slice(0, 2).map((l) => l.n)).toEqual([10, 3])
    act(() => result.current.alternar('nome'))
    expect(result.current.ordem).toEqual({ campo: 'nome', dir: 'asc' })
  })
})
