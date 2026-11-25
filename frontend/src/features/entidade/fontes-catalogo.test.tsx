// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import '../asn'
import '../operadora'
import '../ptt'
import '../grupo'
import '../uf'
import { todosOsBlocos } from './registry'

const fontesCatalogo: string[] = JSON.parse(readFileSync(resolve(__dirname, '../../../../docs/fontes.json'), 'utf-8')).fontes.map((f: { id: string }) => f.id)

describe('fontes declaradas pelos blocos de todas as entidades', () => {
  // arquivo à parte: importar o grupo e a UF no registro de `registry.test.tsx` mudaria as entidades que os testes de abas usam
  it('FONT-E5: todo bloco, inclusive os do grupo e da UF, só declara id que existe no catálogo (o id `rpki` não existe: é `rpki_collector`)', () => {
    const entidades = new Set(todosOsBlocos().map((b) => b.entidade))
    expect([...entidades]).toEqual(expect.arrayContaining(['asn', 'operadora', 'ixp', 'grupo', 'uf']))
    expect(todosOsBlocos().some((b) => b.entidade === 'grupo' && b.fontes.includes('rpki_collector'))).toBe(true)
    for (const b of todosOsBlocos()) for (const f of b.fontes) expect(fontesCatalogo, `${b.entidade}/${b.id}: fonte ${f} fora do catálogo`).toContain(f)
  })
})
