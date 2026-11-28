// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { COR_SEM_DADO } from '../components/maps/coresCoropletico'
import { VISAO_ALCANCE_DIRETOS, VISAO_ALCANCE_TODOS, VISAO_DIRETOS, VISAO_TODOS } from '../features/ptt/areaInfluencia.fixture'
import { corPtt, expressaoFaixas, expressaoPrincipal, formatarKm, frasesAlcance, frasesArea, MATIZES, matizesPorPtt, pct, TONS_UM_MATIZ } from './areaInfluencia'

describe('formatarKm e pct', () => {
  it('arredonda para km inteiro com separador de milhar e trata menos de 1 km', () => {
    expect(formatarKm(1189.3)).toBe('1.189 km')
    expect(formatarKm(12.4)).toBe('12 km')
    expect(formatarKm(0.2)).toBe('menos de 1 km')
    expect(pct(50, 200)).toBe('25%')
    expect(pct(1, 0)).toBe('0%')
  })
})

describe('matizesPorPtt', () => {
  const ptts = {
    sp: { ponto: [-23.5, -46.6] as [number, number], municipios: 900 },
    cas: { ponto: [-22.9, -47.0] as [number, number], municipios: 300 },
    rj: { ponto: [-22.9, -43.2] as [number, number], municipios: 500 },
    mg: { ponto: [-19.9, -43.9] as [number, number], municipios: 600 },
    am: { ponto: [-3.1, -60.0] as [number, number], municipios: 20 },
    sem: { ponto: null, municipios: 5 },
  }

  it('dá um matiz a cada PTT e PTTs vizinhos não repetem o matiz', () => {
    const m = matizesPorPtt(ptts)
    expect(Object.keys(m).sort()).toEqual(Object.keys(ptts).sort())
    for (const v of Object.values(m)) expect(MATIZES).toContain(v)
    expect(new Set([m.sp, m.cas, m.rj, m.mg]).size).toBe(4)                 // os quatro do Sudeste são vizinhos entre si
  })

  it('é determinística e funciona sem coordenada', () => {
    expect(matizesPorPtt(ptts)).toEqual(matizesPorPtt({ ...ptts }))
    expect(matizesPorPtt({ a: { ponto: null, municipios: 1 }, b: { ponto: null, municipios: 1 } })).toEqual({ a: MATIZES[0], b: MATIZES[1] })
  })

  it('com mais PTTs que matizes, repete o mais longe', () => {
    const muitos = Object.fromEntries(Array.from({ length: 30 }, (_, i) => [`p${i}`, { ponto: [-30 + i * 0.5, -50 + i * 0.5] as [number, number], municipios: 100 - i }]))
    const m = matizesPorPtt(muitos)
    expect(Object.keys(m)).toHaveLength(30)
    for (let i = 0; i < 29; i++) expect(m[`p${i}`]).not.toBe(m[`p${i + 1}`])       // vizinhos imediatos nunca repetem
  })
})

describe('expressões de cor', () => {
  it('a do PTT agrupa os municípios por faixa nos três tons de um só matiz e deixa o resto cinza', () => {
    const e = expressaoFaixas({ '1': [10, 1], '2': [5, 2], '3': [1, 3], '4': [9, 1] }) as unknown[]
    expect(e[0]).toBe('match')
    expect(e[1]).toEqual(['get', 'ibge'])
    expect(e).toContain(TONS_UM_MATIZ[1]); expect(e).toContain(TONS_UM_MATIZ[2]); expect(e).toContain(TONS_UM_MATIZ[3])
    expect(e[2]).toEqual(['1', '4'])
    expect(e[e.length - 1]).toBe(COR_SEM_DADO)
    expect(expressaoFaixas({})).toBe(COR_SEM_DADO)
  })

  it('a nacional usa o matiz do PTT principal e o tom da faixa; PTT sem matiz fica cinza', () => {
    const e = expressaoPrincipal({ a: ['sp', 1, 1, 1, 1], b: ['sp', 3, 1, 1, 1], c: ['rj', 1, 1, 1, 1], d: ['xx', 2, 1, 1, 1] }, { sp: 210, rj: 30 }) as unknown[]
    expect(e).toContain(corPtt(210, 1)); expect(e).toContain(corPtt(210, 3)); expect(e).toContain(corPtt(30, 1))
    expect(e.flat()).not.toContain('d')
    expect(corPtt(210, 1)).not.toBe(corPtt(210, 3))
    expect(e[e.length - 1]).toBe(COR_SEM_DADO)
  })

  it('nenhum matiz é vermelho (alerta)', () => {
    for (const m of MATIZES) expect(m > 20 && m < 340).toBe(true)
  })
})

describe('frasesArea', () => {
  it('responde às duas perguntas com os números das visões', () => {
    const f = frasesArea(VISAO_DIRETOS, VISAO_TODOS)
    expect(f.diretos).toBe('Os participantes diretamente conectados atuam, na maior parte (P50), a até 12 km; quase todos (P80), a até 80 km; os restantes, além disso (o P90 é 151 km).')
    expect(f.todos).toMatch(/^Considerando também quem anuncia pelo PTT sem estar conectado, a área chega a 200 km para quase todos os acessos \(P80\) e a 410 km no P90; a maior parte \(P50\) está a até 20 km\./)
    expect(f.todos).toContain('Entram na conta 6 operadoras em 4 municípios, contra 4 em 3 só com os conectados.')
    expect(f.mediana).toContain('A mediana por operadora é de 55 km (cada operadora conta uma vez)')
    expect(f.mediana).toContain('outra população que o P50')
  })

  it('usa o singular pelo número e diz quando uma visão não tem acessos atribuídos', () => {
    const um = { ...VISAO_TODOS, operadoras: 1, municipios: 1 }
    expect(frasesArea(VISAO_DIRETOS, um).todos).toContain('Entram na conta 1 operadora em 1 município,')
    const f = frasesArea(null, VISAO_TODOS)
    expect(f.diretos).toMatch(/^Nenhum participante diretamente conectado/)
    expect(f.todos).not.toContain('contra')
    expect(frasesArea(null, null)).toEqual({ diretos: expect.stringMatching(/^Nenhum participante diretamente conectado/), todos: expect.stringMatching(/^Nenhum ASN com prefixo próprio/), mediana: null })
  })

  it('o texto não tem travessão nem "(s)"', () => {
    const f = frasesArea(VISAO_DIRETOS, VISAO_TODOS)
    expect(Object.values(f).join(' ')).not.toMatch(/[—–]|\(s\)/)
  })
})

describe('frasesAlcance', () => {
  it('diz o alcance sem descontar PTTs mais próximos, com os números das duas visões', () => {
    const f = frasesAlcance(VISAO_ALCANCE_DIRETOS, VISAO_ALCANCE_TODOS)
    expect(f.diretos).toBe('Considerando todos os municípios onde atuam as operadoras diretamente conectadas, sem descontar PTTs mais próximos, a maioria (P50) está a até 40 km; quase todos (P80), a até 300 km; o P90 é 520 km.')
    expect(f.todos).toMatch(/^Considerando todos os municípios onde atuam as operadoras que anunciam pelo PTT, diretas e indiretas, sem descontar PTTs mais próximos, a maioria \(P50\) está a até 60 km; quase todos \(P80\), a até 350 km; o P90 é 610 km\./)
    expect(f.todos).toContain('O alcance reúne 6 operadoras em 4 municípios, contra 4 em 4 só com as conectadas.')
    expect(f.mediana).toContain('No alcance, a mediana por operadora é de 90 km')
    expect(Object.values(f).join(' ')).not.toMatch(/[—–]|\(s\)/)
  })

  it('usa o singular pelo número e diz quando uma visão não tem operadoras', () => {
    const um = { ...VISAO_ALCANCE_TODOS, operadoras: 1, municipios: 1 }
    expect(frasesAlcance(null, um).todos).toContain('O alcance reúne 1 operadora em 1 município.')
    expect(frasesAlcance(null, null)).toEqual({ diretos: expect.stringMatching(/^Nenhum participante diretamente conectado/), todos: expect.stringMatching(/^Nenhum ASN com prefixo próprio/), mediana: null })
  })
})
