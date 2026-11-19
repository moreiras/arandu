// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { tituloDaRota, TITULO_HOME } from './tituloRota'

describe('tituloDaRota', () => {
  it('home, entidades e páginas do menu', () => {
    expect(tituloDaRota('/')).toBe(TITULO_HOME)
    expect(tituloDaRota('/asn/64496')).toBe('AS64496 · Arandurapé')
    expect(tituloDaRota('/ixp/sp')).toBe('PTT sp · Arandurapé')
    expect(tituloDaRota('/uf/es')).toBe('UF ES · Arandurapé')
    expect(tituloDaRota('/estatisticas')).toBe('Estatísticas · Arandurapé')
    expect(tituloDaRota('/privacidade')).toBe('Política de privacidade · Arandurapé')
  })
  it('prefixo com barra e rota desconhecida', () => {
    expect(tituloDaRota('/prefixo/198.18.0.0/24')).toBe('Prefixo 198.18.0.0/24 · Arandurapé')
    expect(tituloDaRota('/nao-existe')).toBe('Arandurapé')
  })
})
