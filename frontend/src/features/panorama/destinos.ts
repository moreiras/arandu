// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Onde fica cada bloco das rotas Visão geral e Estatísticas, que viraram aliases dos panoramas. Nenhuma informação fica sem lugar; o teste confere
 * que cada destino é uma aba que existe. A página de origem segue em `?versao=1`. Cobertura de endereços fica nas abas IPv6/IPv4, ASNs por PTT em
 * Interconexão e o mapa no fim do Resumo; a tabela de referência fica só em PTTs (/ixps). Rankings do SICI continua como página própria.
 */
/** `para` é uma aba de panorama ou, quando o bloco já tinha uma página de detalhe, essa página (`PAGINAS_DE_DETALHE`). */
export interface Destino { de: 'visao-geral' | 'estatisticas'; bloco: string; para: string }

export const PAGINAS_DE_DETALHE = ['/ixps']

export const DESTINOS: Destino[] = [
  { de: 'visao-geral', bloco: 'Saúde do snapshot, KPIs e painel de estatísticas', para: '/panorama/tecnico' },
  { de: 'visao-geral', bloco: 'Mapa de ASNs brasileiros (visibilidade na tabela global)', para: '/panorama/tecnico' },
  { de: 'visao-geral', bloco: 'Espaço IPv6 (curva de Hilbert /32)', para: '/panorama/tecnico?aba=ipv6' },
  { de: 'visao-geral', bloco: 'Espaço IPv4 (curva de Hilbert /16)', para: '/panorama/tecnico?aba=ipv4' },
  { de: 'visao-geral', bloco: 'Tabela de referência (tabela global × IX.br)', para: '/ixps' },
  { de: 'estatisticas', bloco: 'Visão geral: AS, IPv6, IPv4, Registro.br, UF e macrorregião', para: '/panorama/tecnico' },
  { de: 'estatisticas', bloco: 'Grupos econômicos (CNPJs com vários ASNs)', para: '/panorama/mercado?aba=grupos' },
  { de: 'estatisticas', bloco: 'Cobertura IPv4 no IX.br (prefixos BR e full table)', para: '/panorama/tecnico?aba=ipv4' },
  { de: 'estatisticas', bloco: 'Cobertura IPv6 no IX.br (prefixos BR e full table)', para: '/panorama/tecnico?aba=ipv6' },
  { de: 'estatisticas', bloco: 'ASNs diretos, originadores e originadores BR por PTT', para: '/panorama/tecnico?aba=interconexao' },
  { de: 'estatisticas', bloco: 'Segurança de roteamento', para: '/panorama/tecnico?aba=seguranca' },
  { de: 'estatisticas', bloco: 'Banda larga fixa (SCM)', para: '/panorama/mercado?aba=banda-larga-fixa' },
  { de: 'estatisticas', bloco: 'Banda larga móvel (SMP)', para: '/panorama/mercado?aba=banda-larga-movel' },
  { de: 'estatisticas', bloco: 'Telefonia fixa (STFC)', para: '/panorama/mercado?aba=telefonia-fixa' },
  { de: 'estatisticas', bloco: 'TV por assinatura (SeAC)', para: '/panorama/mercado?aba=tv-por-assinatura' },
]

/** Para onde cada página antiga redireciona por padrão (o primeiro bloco dela). */
export const ALIAS: Record<Destino['de'], string> = { 'visao-geral': '/panorama/tecnico', estatisticas: '/panorama/tecnico' }
