// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Menu por tema. Fonte única: o AppLayout, a gaveta do celular, o teste de rotas e o E2E leem esta lista.
 * Seis grupos. Só entram rotas que existem; rotas que mudaram de lugar continuam respondendo (aliases).
 * Formato: o E2E (`tests/e2e/menu.js`) lê os campos por expressão regular; mantenha cada item numa linha.
 */
export interface ItemMenu { rotulo: string; to: string; descricao?: string; ativoEm?: string[]; externo?: boolean }
export interface GrupoMenu { id: string; rotulo: string; itens: ItemMenu[] }

export const GRUPOS_MENU: GrupoMenu[] = [
  { id: 'rede', rotulo: 'Rede', itens: [
    { rotulo: 'Panorama técnico', to: '/panorama/tecnico', descricao: 'A rede brasileira em números: IPv6, IPv4, interconexão, CDNs e segurança (RPKI, ROV, DNSSEC)', ativoEm: ['/visao-geral', '/panorama/ipv6'] },
    { rotulo: 'ASes', to: '/ases', descricao: 'Redes autônomas do Brasil, com prefixos, ROAs e relações', ativoEm: ['/asn/'] },
    { rotulo: 'Tabela BGP', to: '/bgp', descricao: 'Análises da tabela global: agregação, cobertura e estabilidade' },
    { rotulo: 'Segurança de roteamento', to: '/seguranca-de-roteamento', descricao: 'Prontidão, RPKI e ROV por UF e porte, MANRS e metodologia' },
    { rotulo: 'Mercado IPv4', to: '/mercado-ipv4', descricao: 'Mercado secundário: transferências, espaço sem uso e uso por terceiros' },
  ] },
  { id: 'interconexao', rotulo: 'Interconexão', itens: [
    { rotulo: 'Panorama da interconexão', to: '/panorama/tecnico?aba=interconexao', descricao: 'PTTs, participantes, alcance e CDNs no agregado (aba do Panorama técnico)' },
    { rotulo: 'PTTs', to: '/ixps', descricao: 'Pontos de troca de tráfego (IXPs), participantes e cobertura', ativoEm: ['/ixp/', '/ixp-externo/'] },
    { rotulo: 'CDNs e conteúdo', to: '/cdns', descricao: 'Onde cada CDN está presente e o que alcança', ativoEm: ['/cdncap/'] },
    { rotulo: 'Datacenters', to: '/instalacoes', descricao: 'Instalações de colocation e as redes presentes', ativoEm: ['/instalacao/'] },
    { rotulo: 'Route servers e communities', to: '/communities', descricao: 'Communities dos route servers por PTT' },
  ] },
  { id: 'mercado', rotulo: 'Mercado', itens: [
    { rotulo: 'Operadoras', to: '/operadoras', descricao: 'Provedores e operadoras: assinantes, outorgas e rede', ativoEm: ['/operadora/', '/scms', '/smps', '/stfcs', '/seacs'] },
    { rotulo: 'Grupos econômicos', to: '/grupos', descricao: 'Empresas que pertencem ao mesmo grupo' },
    { rotulo: 'Panorama de mercado', to: '/panorama/mercado', descricao: 'Banda larga, telefonia e TV por assinatura, por serviço', ativoEm: ['/estatisticas'] },
    { rotulo: 'Rankings do SICI', to: '/rankings', descricao: 'Operadoras por acessos declarados e outorgas sem declaração (abre em Operadoras)' },
  ] },
  { id: 'regulacao', rotulo: 'Regulação e qualidade', itens: [
    { rotulo: 'Qualidade e reclamações', to: '/qualidade', descricao: 'Indicadores de qualidade e reclamações dos consumidores' },
    { rotulo: 'Regulatório', to: '/regulatorio', descricao: 'FUST, multas, espectro e satélites' },
  ] },
  { id: 'territorio', rotulo: 'Território', itens: [
    { rotulo: 'Mapa', to: '/mapa', descricao: 'Redes, PTTs e prefixos no mapa do Brasil' },
    { rotulo: 'Estados', to: '/estados', descricao: 'Cada UF: mercado, rede e interconexão', ativoEm: ['/uf/'] },
    { rotulo: 'Municípios', to: '/municipios', descricao: 'Lista e mapa dos municípios, por mercado, penetração e distância a PTT' },
    { rotulo: 'Localizador', to: '/localizador', descricao: 'Procure um município e veja o que existe ao redor', ativoEm: ['/municipio/'] },
    { rotulo: 'Uso da Internet', to: '/uso-da-internet', descricao: 'Indicadores de uso da Internet no Brasil' },
  ] },
  { id: 'dados', rotulo: 'Dados', itens: [
    { rotulo: 'O que mudou', to: '/mudancas', descricao: 'Diferenças entre dois snapshots' },
    { rotulo: 'Explorar dados', to: '/explorar', descricao: 'Filtre e cruze os conjuntos de dados' },
    { rotulo: 'API e MCP', to: '/dados', descricao: 'Acesso programático e para assistentes de IA' },
    { rotulo: 'Fontes e metodologia', to: '/fontes', descricao: 'De onde vem cada dado, com data e frescor' },
    { rotulo: 'Snapshots', to: '/snapshots', descricao: 'Versões datadas e imutáveis dos dados' },
    { rotulo: 'Sobre', to: '/sobre', descricao: 'O projeto, a licença e os créditos' },
    { rotulo: 'Mapa do site', to: '/mapa-do-site', descricao: 'Todas as páginas, por tema' },
  ] },
]

/**
 * Ferramentas transversais, fora dos grupos temáticos: o comparador serve a PTTs, ASes, operadoras, municípios e datas, e por isso não pertence
 * a Interconexão. Aparecem como botão avulso depois dos grupos no menu e na gaveta do celular. O E2E (`tests/e2e/menu.js`) lê esta lista pelo marcador abaixo.
 */
export const ITENS_AVULSOS: ItemMenu[] = [
  { rotulo: 'Comparar', to: '/comparar', descricao: 'PTTs, ASes, operadoras, municípios ou datas lado a lado' },
]

/** `to` pode trazer query (`/operadoras?servico=smp`): nesse caso o parâmetro também precisa bater (sem `servico`, vale SCM, o padrão da página). */
export function itemAtivo(item: ItemMenu, pathname: string, search = ''): boolean {
  if (item.externo) return false
  const [caminho, consulta] = item.to.split('?')
  if (consulta) {
    const esperado = new URLSearchParams(consulta)
    const atual = new URLSearchParams(search)
    const noCaminho = pathname === caminho && [...esperado].every(([k, v]) => (atual.get(k) ?? (k === 'servico' ? 'scm' : '')) === v)
    return noCaminho || (item.ativoEm ?? []).some((p) => pathname.startsWith(p))
  }
  return pathname === caminho || pathname.startsWith(caminho + '/') || (item.ativoEm ?? []).some((p) => pathname.startsWith(p))
}

export function grupoAtivo(g: GrupoMenu, pathname: string, search = ''): boolean {
  return g.itens.some((i) => itemAtivo(i, pathname, search))
}
