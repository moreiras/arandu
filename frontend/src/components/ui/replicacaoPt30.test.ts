// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Replicação do PT-30 no resto do site: nenhuma página usa mais a síntese antiga, e nas páginas com cartões o resumo vem depois deles. */
import { describe, expect, it } from 'vitest'

const fontes = import.meta.glob(['../../**/*.tsx', '../../**/*.ts', '!../../**/*.test.*', '!../../test/**'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const de = (fim: string) => Object.entries(fontes).find(([k]) => k.endsWith(fim))?.[1] ?? ''
const semComentarios = (v: string) => v.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/.*$/gm, '')

describe('replicação do PT-30', () => {
  it('nenhum arquivo, além do próprio componente e do índice, usa o SinteseTopo (o arquivo fica até a remoção ser decidida)', () => {
    const usuarios = Object.entries(fontes)
      .filter(([k]) => k !== './SinteseTopo.tsx' && k !== './index.ts')
      .filter(([, v]) => /\bSinteseTopo\b/.test(semComentarios(v)))
      .map(([k]) => k)
    expect(usuarios).toEqual([])
  })

  it('em /ixps os cartões vêm antes do resumo em texto, no mesmo grupo de fontes', () => {
    const s = de('/pages/IXPs.tsx')
    const grupo = s.indexOf('<GrupoFontes')
    expect(grupo).toBeGreaterThan(0)
    expect(s.indexOf('<IXPsKpis')).toBeGreaterThan(grupo)
    expect(s.indexOf('<ResumoEmTexto')).toBeGreaterThan(s.indexOf('<IXPsKpis'))
  })

  it('no Panorama técnico o resumo vem depois dos temas de cartões', () => {
    const s = de('/features/panorama/ResumoTecnico.tsx')
    expect(s.indexOf('<ResumoEmTexto')).toBeGreaterThan(s.lastIndexOf('</Tema>'))
  })

  it('as páginas replicadas ligam a apresentação recolhida', () => {
    for (const f of ['/pages/IXPs.tsx', '/pages/IXPPage.tsx', '/pages/UFPage.tsx', '/pages/CDNPage.tsx', '/pages/MunicipiosPage.tsx', '/pages/UsoInternetPage.tsx', '/features/panorama/PaginaPanorama.tsx']) {
      expect(de(f), f).toMatch(/<ApresentacaoRecolhida>/)
    }
  })
})
