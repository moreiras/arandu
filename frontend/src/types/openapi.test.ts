// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import openapiTS, { astToString } from 'openapi-typescript'
import { expect, it } from 'vitest'

// Diff vazio dos tipos gerados: openapi.gen.ts tem de ser exatamente o que o gerador produz de openapi.json.
// Se falhar: `python3 scripts/gen_openapi.py && bash scripts/front-test.sh --gen-tipos` e commite os dois arquivos.
it('openapi.gen.ts está em dia com openapi.json', async () => {
  const dir = resolve(__dirname)
  const ast = await openapiTS(new URL(`file://${dir}/openapi.json`))
  const esperado = astToString(ast)
  const atual = readFileSync(`${dir}/openapi.gen.ts`, 'utf-8')
  const norm = (t: string) => t.replace(/\s+$/gm, '').trim()
  expect(norm(atual).endsWith(norm(esperado))).toBe(true)
})
