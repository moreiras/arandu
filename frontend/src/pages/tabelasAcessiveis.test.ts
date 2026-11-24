// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Tabelas montadas à mão nas páginas revistas no PT-29 (GRUPO-E1, USO-E13, CDNS-E7): todo <th> de cabeçalho com `scope` e toda
 * <table> com nome (caption ou aria-label), para o leitor de tela associar célula e cabeçalho e anunciar o título da tabela.
 */
const ARQUIVOS = [
  'pages/QualidadePage.tsx', 'pages/RegulatorioPage.tsx', 'pages/RankingsPage.tsx', 'pages/UsoInternetPage.tsx', 'pages/CDNPage.tsx',
  'features/qualidade/consumidor.tsx', 'features/grupo/blocks/MercadoBlocos.tsx', 'features/grupo/blocks/RegulatorioTecnicoBlocos.tsx',
  'components/stats/OrganizacoesVariosAsns.tsx', 'features/operadora/RedeSection.tsx',
]

describe('tabelas com scope e nome (PT-29)', () => {
  for (const rel of ARQUIVOS) {
    it(rel, () => {
      const fonte = readFileSync(resolve(__dirname, '..', rel), 'utf-8')
      const semScope = [...fonte.matchAll(/<th\b(?![^>]*\bscope=)[^>]*>/g)].map((m) => m[0])
      expect(semScope, 'th sem scope').toEqual([])
      const tabelas = [...fonte.matchAll(/<table\b[^>]*>\s*(<caption\b)?/g)]
      expect(tabelas.length).toBeGreaterThan(0)
      for (const t of tabelas) expect(/aria-label=/.test(t[0]) || !!t[1], t[0]).toBe(true)
    })
  }
})
