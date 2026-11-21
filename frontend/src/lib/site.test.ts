// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { afterEach, describe, expect, it, vi } from 'vitest'

async function siteCom(nome: string, mcp: string) {
  vi.stubEnv('VITE_SITE_NOME', nome)
  vi.stubEnv('VITE_SITE_MCP_ESQUEMA', mcp)
  vi.resetModules()
  return import('./site')
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('comIdentidade', () => {
  it('troca o nome do software pelo do site nos valores, nunca nas chaves', async () => {
    const { comIdentidade } = await siteCom('Observatório Exemplo', 'exemplo')
    const antes = {
      nota: 'Estimativa do Arandurapé, não número do Cetic.br.',
      campos: [{ nome: 'natureza', significado: "Sempre 'estimativa_arandurape': calculado pelo ARANDURAPE." }],
      recurso: 'arandurape://glossario',
      estimativa_arandurape: 1,
      n: 3,
      vazio: null,
    }
    expect(comIdentidade(antes)).toEqual({
      nota: 'Estimativa do Observatório Exemplo, não número do Cetic.br.',
      campos: [{ nome: 'natureza', significado: "Sempre 'estimativa_arandurape': calculado pelo Observatório Exemplo." }],
      recurso: 'exemplo://glossario',
      estimativa_arandurape: 1,
      n: 3,
      vazio: null,
    })
  })

  it('não toca palavra que só contém o nome nem o nome do software em minúsculas', async () => {
    const { comIdentidade } = await siteCom('Exemplo', 'exemplo')
    expect(comIdentidade('Arandurapés, xArandurapé, User-Agent arandurape/2.0')).toBe('Arandurapés, xArandurapé, User-Agent arandurape/2.0')
    expect(comIdentidade('(Arandurapé).')).toBe('(Exemplo).')
  })
})
