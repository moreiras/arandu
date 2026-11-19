// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MenuTema } from './MenuTema'
import { GRUPOS_MENU, ITENS_AVULSOS, grupoAtivo, itemAtivo } from './menu'

const main = readFileSync(resolve(__dirname, '../../main.tsx'), 'utf-8')
const rotas = [...main.matchAll(/<Route path="([^"]+)"/g)].map((m) => '/' + m[1])

describe('menu por tema', () => {
  it('tem os 6 grupos decididos no portão 1, na ordem', () => {
    expect(GRUPOS_MENU.map((g) => g.rotulo)).toEqual(['Rede', 'Interconexão', 'Mercado', 'Regulação e qualidade', 'Território', 'Dados'])
  })

  it('todo item tem uma linha de descrição (megamenu)', () => {
    for (const g of GRUPOS_MENU) for (const i of g.itens) expect(i.descricao, `${g.rotulo} › ${i.rotulo}`).toBeTruthy()
  })

  it('nenhuma rota some do menu: toda rota de lista da versão anterior segue alcançável', () => {
    // itens de menu publicados; "Sitemap" e os demais seguem no menu, os que mudaram de grupo continuam presentes
    const anteriores = ['/panorama/tecnico', '/ases', '/bgp', '/ixps', '/cdns', '/instalacoes', '/comparar', '/communities', '/operadoras', '/grupos', '/panorama/mercado', '/rankings', '/uso-da-internet', '/mercado-ipv4', '/regulatorio', '/qualidade', '/seguranca-de-roteamento', '/mudancas', '/mapa', '/estados', '/localizador', '/explorar', '/snapshots', '/dados', '/fontes', '/mapa-do-site', '/sobre']
    // o item de menu é "Mapa do site" (página para pessoas), que tem o link para o XML
    const atuais = [...GRUPOS_MENU.flatMap((g) => g.itens), ...ITENS_AVULSOS].map((i) => i.to.split('?')[0])
    for (const a of anteriores) expect(atuais, a).toContain(a)
  })

  it('todo link aponta para uma rota que existe (nenhum link quebrado)', () => {
    for (const g of GRUPOS_MENU) for (const i of g.itens.filter((x) => !x.externo)) expect(rotas, `${g.rotulo} › ${i.rotulo}`).toContain(i.to.split('?')[0])
  })

  it('Comparar é um item avulso (não pertence a um tema): tem descrição, rota existente e acende em qualquer aba do comparador', () => {
    expect(GRUPOS_MENU.flatMap((g) => g.itens).some((i) => i.to.startsWith('/comparar'))).toBe(false)
    const comparar = ITENS_AVULSOS.find((i) => i.to === '/comparar')!
    expect(comparar.descricao).toBeTruthy()
    expect(rotas).toContain('/comparar')
    for (const consulta of ['', '?tipo=asn&ids=1,2', '?modo=datas', '?ixp=sp,rj']) expect(itemAtivo(comparar, '/comparar', consulta), consulta).toBe(true)
  })

  it('páginas de detalhe acendem o grupo da lista de origem', () => {
    const rede = GRUPOS_MENU[0]
    expect(grupoAtivo(rede, '/asn/64496')).toBe(true)
    expect(grupoAtivo(GRUPOS_MENU[1], '/ixp/sp')).toBe(true)
    expect(itemAtivo({ rotulo: 'x', to: '/bgp' }, '/bgpx')).toBe(false)
  })

  it('Operadoras (Mercado) acende em /operadoras (qualquer serviço) e nas rotas antigas de outorga', () => {
    const mercado = GRUPOS_MENU[2]
    for (const [caminho, consulta] of [['/operadoras', ''], ['/operadoras', '?servico=smp'], ['/operadora/123', ''], ['/smps', '']] as const) {
      expect(grupoAtivo(mercado, caminho, consulta), caminho + consulta).toBe(true)
    }
  })

  it('itemAtivo com parâmetro na URL do item: sem `servico` na página vale SCM, o padrão', () => {
    const smp = { rotulo: 'x', to: '/operadoras?servico=smp' }
    const scm = { rotulo: 'y', to: '/operadoras?servico=scm' }
    expect(itemAtivo(smp, '/operadoras', '?uf=SP&servico=smp')).toBe(true)
    expect(itemAtivo(scm, '/operadoras', '?servico=smp')).toBe(false)
    expect(itemAtivo(scm, '/operadoras', '')).toBe(true)
  })
})

describe('MenuTema', () => {
  const montar = (path = '/') => render(<MemoryRouter initialEntries={[path]}><MenuTema /></MemoryRouter>)

  it('clicar abre o grupo com os links; clicar de novo fecha', () => {
    montar()
    const b = screen.getByRole('button', { name: 'Rede' })
    expect(b).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(b)
    expect(b).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('menuitem', { name: 'ASes' })).toHaveAttribute('href', '/ases')
    fireEvent.click(b)
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('só um grupo aberto por vez', () => {
    montar()
    fireEvent.click(screen.getByRole('button', { name: 'Rede' }))
    fireEvent.click(screen.getByRole('button', { name: 'Mercado' }))
    expect(screen.getAllByRole('menu')).toHaveLength(1)
    expect(screen.getByRole('menu')).toHaveAccessibleName('Mercado')
  })

  it('↓ abre, foca o primeiro item; ↓↑ percorrem em círculo; Esc fecha e devolve o foco', async () => {
    montar()
    const b = screen.getByRole('button', { name: 'Território' })
    b.focus()
    fireEvent.keyDown(b, { key: 'ArrowDown' })
    const itens = await screen.findAllByRole('menuitem')
    expect(document.activeElement).toBe(itens[0])
    fireEvent.keyDown(itens[0], { key: 'ArrowUp' })
    expect(document.activeElement).toBe(itens[itens.length - 1])
    fireEvent.keyDown(itens[itens.length - 1], { key: 'ArrowDown' })
    expect(document.activeElement).toBe(itens[0])
    fireEvent.keyDown(itens[0], { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(b)
  })

  it('o botão do grupo da página atual fica destacado', () => {
    montar('/smps')
    expect(screen.getByRole('button', { name: 'Mercado' }).className).toContain('bg-primario-100')
    expect(screen.getByRole('button', { name: 'Rede' }).className).not.toContain('bg-primario-100')
  })
})
