// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { GRUPOS_MENU } from './menu'
import { MARCA, tituloDaRota } from './tituloRota'

const main = readFileSync(resolve(__dirname, '../../main.tsx'), 'utf-8')
const rotas = [...main.matchAll(/<Route path="([^"]+)"/g)].map((m) => '/' + m[1])

/**
 * Rotas publicadas (regra 8 do AGENTS.md: nada some sem alias). Rota que mudar de nome ou for dissolvida continua nesta
 * lista e precisa seguir respondendo em main.tsx (redirecionando, com a query preservada); só sai daqui com decisão registrada.
 */
const ROTAS_V15 = [
  '/visao-geral', '/fontes', '/dados', '/sobre', '/privacidade', '/ixps', '/ases', '/scms', '/smps', '/stfcs', '/seacs', '/operadoras', '/grupos',
  '/operadora/:cnpj', '/prefixo/*', '/explorar', '/estados', '/uf/:uf', '/municipio/:ibge', '/ixp/:code', '/ixp-externo/:code', '/instalacoes',
  '/instalacao/:id', '/asn/:asn', '/cdns', '/cdncap/:slug', '/estatisticas', '/rankings', '/communities', '/uso-da-internet', '/mercado-ipv4',
  '/regulatorio', '/qualidade', '/seguranca-de-roteamento', '/mudancas', '/comparar', '/snapshots', '/localizador', '/mapa', '/bgp', '/login',
]

describe('rotas (aliases e títulos)', () => {
  it('os três panoramas existem e as páginas dissolvidas viraram alias', () => {
    for (const r of ['/panorama/tecnico', '/panorama/mercado', '/panorama/ipv6']) expect(rotas, r).toContain(r)
    expect(main).toMatch(/path="visao-geral" element=\{<AliasPanorama/)
    expect(main).toMatch(/path="estatisticas" element=\{<AliasPanorama/)
  })

  it('toda rota publicada até a v1.5 continua respondendo', () => {
    for (const r of ROTAS_V15) expect(rotas, r).toContain(r)
  })

  it('100% das rotas de página têm título próprio (não só a marca)', () => {
    const exemplo = (r: string) => r.replace(':cnpj', '123').replace(':ibge', '3205309').replace(':code', 'sp').replace(':id', 'x').replace(':asn', '64500').replace(':slug', 'google').replace(':uf', 'es').replace('*', '10.0.0.0/8')
    const semTitulo = rotas.filter((r) => !['/', '/*'].includes(r)).filter((r) => tituloDaRota(exemplo(r)) === MARCA)
    expect(semTitulo).toEqual([])
  })

  it('títulos de entidade levam o identificador e a marca', () => {
    expect(tituloDaRota('/asn/64500')).toBe(`AS64500 · ${MARCA}`)
    expect(tituloDaRota('/uf/es')).toBe(`UF ES · ${MARCA}`)
  })

  it('páginas do menu têm o rótulo do menu no título', () => {
    // Item que abre uma aba de outra página do menu (`?aba=`, como "Panorama da interconexão") leva o título da página: o título é por caminho.
    for (const g of GRUPOS_MENU) for (const i of g.itens.filter((x) => !x.externo && !x.to.includes('aba='))) expect(tituloDaRota(i.to.split('?')[0]), i.to).toContain(i.rotulo)
  })
})
