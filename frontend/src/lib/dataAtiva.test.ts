// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { comData, manterData } from './dataAtiva'

const ANTIGA = '2026-09-13'

function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    return statSync(p).isDirectory() ? arquivos(p) : /\.(ts|tsx)$/.test(n) && !/\.test\.tsx?$/.test(n) ? [p] : []
  })
}

describe('comData (PT-02)', () => {
  it('acrescenta a data a caminhos internos, antes da âncora e depois dos parâmetros existentes', () => {
    expect(comData('/asn/1916', ANTIGA)).toBe('/asn/1916?date=2026-09-13')
    expect(comData('/comparar?tipo=asn&ids=1,2', ANTIGA)).toBe('/comparar?tipo=asn&ids=1,2&date=2026-09-13')
    expect(comData('/ixp/sp#bloco-membros', ANTIGA)).toBe('/ixp/sp?date=2026-09-13#bloco-membros')
    expect(comData('/x?', ANTIGA)).toBe('/x?date=2026-09-13')
  })
  it('não mexe sem data, em destino que já traz data, em endereço externo nem em âncora pura', () => {
    expect(comData('/asn/1916', null)).toBe('/asn/1916')
    expect(comData('/asn/1916?date=2026-09-20', ANTIGA)).toBe('/asn/1916?date=2026-09-20')
    expect(comData('https://exemplo.invalid/a', ANTIGA)).toBe('https://exemplo.invalid/a')
    expect(comData('//exemplo.invalid/a', ANTIGA)).toBe('//exemplo.invalid/a')
    expect(comData('#bloco', ANTIGA)).toBe('#bloco')
  })
})

describe('manterData (PT-02)', () => {
  it('troca os parâmetros e preserva só a data', () => {
    expect(manterData(new URLSearchParams('aba=fust&uf=SP&date=2026-09-13'), { aba: 'multas' }).toString()).toBe('aba=multas&date=2026-09-13')
    expect(manterData(new URLSearchParams('aba=fust'), {}).toString()).toBe('')
  })
})

describe('Link do site (PT-02)', () => {
  it('nenhum módulo importa o Link de react-router-dom: os links passam por components/layout/LinkDatado e levam a data', () => {
    const raiz = join(__dirname, '..')
    const achados = arquivos(raiz).filter((p) => !p.endsWith('LinkDatado.tsx') && /import \{[^}]*\bLink\b[^}]*\} from 'react-router-dom'/.test(readFileSync(p, 'utf8')))
    expect(achados).toEqual([])
  })
})
