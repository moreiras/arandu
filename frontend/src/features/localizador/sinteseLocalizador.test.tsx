// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese do raio no Localizador (PT-22): região ao vivo, espera de 500 ms, raio vazio dito em texto, frase de mercado só com acessos declarados. */
import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { ESPERA_SINTESE_MS, SinteseLocalizador } from './BlocoSinteseLocalizador'
import { sinteseLocalizador, type EntradaSinteseLocalizador } from './sinteseLocalizador'

const entrada = (over: Partial<EntradaSinteseLocalizador> = {}): EntradaSinteseLocalizador => ({
  radius: 80, entityCounts: { asns: 37, cnpjsComAsn: 30, scms: 12 }, sedesAsn: 25, filteredAsnsCount: 37, nearestIx: 'ce', ixLabel: (c) => `IX ${c === 'ce' ? 'Fortaleza' : c}`,
  ixCounts: { nearMember: 6, anyMember: 7 }, temPresenca: true,
  mercado: { acessos: 87611, operadoras: 9, hhi: 3600, maiorParticipacao: 60, linhas: [] }, municipiosNoRaio: 3, mesReferencia: '2026-09', snapshot: '2026-11-22', ...over,
})

describe('sinteseLocalizador', () => {
  it('Juazeiro do Norte: redes, interconexão e mercado, com selo, fonte e data', () => {
    const f = sinteseLocalizador(entrada())
    expect(f.map((x) => x.id)).toEqual(['raio', 'ix', 'mercado'])
    expect(f[0].texto).toBe('No raio de 80 km há 37 ASNs (25 sedes de AS), em 30 entidades com ASN; 12 com outorga SCM.')
    expect(f[0].selo).toBe('inferido')
    expect(f[1].texto).toBe('Entre 37 ASNs listados no raio, 6 participam de IX Fortaleza (o PTT do IX.br mais próximo do ponto) e 7 de algum PTT do IX.br.')
    expect(f[2].texto).toContain('Nos 3 municípios com centro no raio foram declarados 87.611 acessos de banda larga fixa, de 9 CNPJs; a maior participação é de 60%')
    expect(f[2].dataRef).toBe('2026-09')
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('raio vazio diz que não há rede nem prestador e não gera frases de IX nem de mercado de rede', () => {
    const f = sinteseLocalizador(entrada({ entityCounts: { asns: 0, cnpjsComAsn: 0, scms: 0 }, sedesAsn: 0, filteredAsnsCount: 0, mercado: null }))
    expect(f).toHaveLength(1)
    expect(f[0].texto).toBe('Nenhuma rede ou prestador com sede neste raio de 80 km.')
  })

  it('sem acessos declarados no raio não há frase de mercado; sem índice de presença, não há frase de IX; singular', () => {
    expect(sinteseLocalizador(entrada({ mercado: null })).some((x) => x.id === 'mercado')).toBe(false)
    expect(sinteseLocalizador(entrada({ temPresenca: false })).some((x) => x.id === 'ix')).toBe(false)
    expect(sinteseLocalizador(entrada({ municipiosNoRaio: 1 })).find((x) => x.id === 'mercado')!.texto).toMatch(/^No município com centro no raio/)
    expect(sinteseLocalizador(entrada({ entityCounts: { asns: 1, cnpjsComAsn: 1, scms: 0 }, sedesAsn: 1 }))[0].texto).toContain('1 ASN (1 sede de AS), em 1 entidade')
  })
})

describe('SinteseLocalizador (região ao vivo)', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('sem ponto mostra a instrução numa região status; com ponto, a síntese depois de 500 ms, também como status', () => {
    const { rerender } = render(<SinteseLocalizador marcado={false} entrada={entrada()} />)
    expect(screen.getByRole('status')).toHaveTextContent('Escolha um ponto no mapa')
    rerender(<SinteseLocalizador marcado entrada={entrada()} />)
    expect(screen.queryByTestId('resumo-em-texto')).toBeNull()
    act(() => { vi.advanceTimersByTime(ESPERA_SINTESE_MS + 10) })
    const regiao = screen.getByTestId('resumo-em-texto')
    expect(regiao).toHaveAttribute('role', 'status')
    expect(regiao).toHaveAttribute('aria-live', 'polite')
    expect(regiao).toHaveTextContent('No raio de 80 km há 37 ASNs')
  })

  it('o controle deslizante muda o raio várias vezes: só o último valor é anunciado', () => {
    const { rerender } = render(<SinteseLocalizador marcado entrada={entrada({ radius: 80 })} />)
    act(() => { vi.advanceTimersByTime(ESPERA_SINTESE_MS + 10) })
    for (const r of [90, 100, 120]) { rerender(<SinteseLocalizador marcado entrada={entrada({ radius: r })} />); act(() => { vi.advanceTimersByTime(100) }) }
    expect(screen.getByTestId('resumo-em-texto')).toHaveTextContent('No raio de 80 km')
    act(() => { vi.advanceTimersByTime(ESPERA_SINTESE_MS) })
    expect(screen.getByTestId('resumo-em-texto')).toHaveTextContent('No raio de 120 km')
  })

  it('raio vazio ainda aparece (uma frase basta no localizador)', () => {
    render(<SinteseLocalizador marcado entrada={entrada({ entityCounts: { asns: 0, cnpjsComAsn: 0, scms: 0 }, sedesAsn: 0, filteredAsnsCount: 0, mercado: null })} />)
    act(() => { vi.advanceTimersByTime(ESPERA_SINTESE_MS + 10) })
    expect(screen.getByTestId('resumo-em-texto')).toHaveTextContent('Nenhuma rede ou prestador com sede neste raio de 80 km.')
  })
})
