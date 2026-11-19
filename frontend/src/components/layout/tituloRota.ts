// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { GRUPOS_MENU, ITENS_AVULSOS } from './menu'
import { SITE, TITULO_SITE } from '../../lib/site'

/** Marca no fim do título: o nome do site vem do .env na compilação (`lib/site.ts`). */
export const MARCA = SITE.nome
export const TITULO_HOME = TITULO_SITE

/** Entidades: prefixo da rota → como o título descreve a página (o identificador vem do segmento da URL). */
const ENTIDADES: [string, (id: string) => string][] = [
  ['/asn/', (id) => (/^\d+$/.test(id) ? `AS${id}` : `AS ${id}`)],
  ['/ixp-externo/', (id) => `PTT externo ${id}`],
  ['/ixp/', (id) => `PTT ${id}`],
  ['/operadora/', (id) => `Operadora ${id}`],
  ['/municipio/', (id) => `Município ${id}`],
  ['/uf/', (id) => `UF ${id.toUpperCase()}`],
  ['/grupo/', (id) => `Grupo ${id}`],
  ['/relatorio/', (id) => `Relatório de uma página: ${id.replace(/^[a-z]+\//, '')}`],
  ['/cdncap/', (id) => `CDN/CAP ${id}`],
  ['/instalacao/', (id) => `Instalação ${id}`],
  ['/prefixo/', (id) => `Prefixo ${id}`],
]

const EXTRAS: Record<string, string> = {
  '/privacidade': 'Política de privacidade',
  '/uso-aceitavel': 'Política de uso aceitável',
  '/acessibilidade': 'Acessibilidade',
  '/municipios': 'Municípios',
  '/perfil': 'Perfil',
  '/sobre': 'Sobre',
  '/login': 'Entrar',
  '/rankings': 'Rankings do SICI',
  '/ixps': 'PTTs',
  // rotas dissolvidas em panoramas: seguem respondendo como alias
  '/visao-geral': 'Visão geral',
  '/panorama/ipv6': 'Panorama técnico: IPv6',
  '/estatisticas': 'Estatísticas',
  '/inicio-classico': 'Início',   // alias: a rota redireciona para /
  // rotas antigas que redirecionam para /operadoras?servico=… (alias)
  '/scms': 'Operadoras (SCM)',
  '/smps': 'Operadoras (SMP)',
  '/stfcs': 'Operadoras (STFC)',
  '/seacs': 'Operadoras (SeAC)',
}

/** Rótulos das páginas estáticas: o do menu (fonte única) mais algumas que o menu não lista. */
function rotuloEstatico(pathname: string): string | null {
  for (const g of GRUPOS_MENU) for (const i of g.itens) if (!i.externo && i.to.split('?')[0] === pathname) return i.rotulo
  for (const i of ITENS_AVULSOS) if (i.to.split('?')[0] === pathname) return i.rotulo
  return EXTRAS[pathname] ?? null
}

/** `document.title` da rota: "AS64496 · Arandurapé", "Estatísticas · Arandurapé"... */
export function tituloDaRota(pathname: string): string {
  const p = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname
  if (p === '/') return TITULO_HOME
  for (const [prefixo, rotulo] of ENTIDADES) {
    if (p.startsWith(prefixo) && p.length > prefixo.length) return `${rotulo(decodeURIComponent(p.slice(prefixo.length)))} · ${MARCA}`
  }
  const r = rotuloEstatico(p)
  return r ? `${r} · ${MARCA}` : MARCA
}
