// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Notas de revisão datadas exibidas nas páginas cujos números a revisão alterou (D7). Fonte única, só no front: não há registro
 * estruturado de correções na API (D8); o registro completo de cada correção é o CHANGELOG. Os números vêm do relatório da regeneração
 * (`products.history.regenerar_eventos`) e são conferidos por `notasRevisao.test.ts` contra `notasRevisao.fixture.json`.
 */
export interface ContagemRevisada { tipo: string; antes: number; depois: number }

export interface NotaRevisao {
  id: string
  /** Data da revisão (AAAA-MM-DD). */
  data: string
  titulo: string
  /** Tipos de evento afetados: a nota só aparece quando o filtro da página os inclui. */
  tipos: string[]
  /** Versão da regra de geração dos eventos. */
  regra: number
  o_que_mudou: string
  causa: string
  /** Contagens por tipo numa data de referência. */
  em: { data: string; contagens: ContagemRevisada[]; nota?: string }
  /** Contagens somadas em todas as datas regeneradas. */
  total: { datas: number; de: string; ate: string; contagens: ContagemRevisada[]; inalterados: string }
}

export const NOTAS_REVISAO: NotaRevisao[] = [
  {
    id: 'eventos-roa-aspa-rpki-2026-11-25',
    data: '2026-11-25',
    titulo: 'eventos de ROA, ASPA e RPKI',
    tipos: ['roa_ganho', 'roa_perdido', 'aspa_ganho', 'aspa_perdido', 'rpki_invalido_novo', 'rpki_invalido_resolvido'],
    regra: 2,
    o_que_mudou:
      'A camada de eventos de todos os snapshots foi regenerada com a regra 2: só há evento de ROA, ASPA ou RPKI quando o campo de origem estava coberto nos dois snapshots comparados (campo presente ou documento que passou pela etapa de saúde).',
    causa:
      'O campo ausente era contado como zero. O roa_list de ASNs estrangeiros foi publicado só a partir de 2026-06-28 e deixou de ser publicado em 2026-07-05, e a perda do campo foi registrada como perda de ROA.',
    em: {
      data: '2026-07-05',
      contagens: [
        { tipo: 'roa_perdido', antes: 50127, depois: 63 },
        { tipo: 'aspa_perdido', antes: 1827, depois: 2 },
        { tipo: 'rpki_invalido_resolvido', antes: 1815, depois: 14 },
      ],
      nota: 'Os 63 eventos de roa_perdido restantes são de ASN brasileiro.',
    },
    total: {
      datas: 20, de: '2026-06-28', ate: '2026-11-22',
      contagens: [
        { tipo: 'roa_perdido', antes: 50919, depois: 834 },
        { tipo: 'aspa_perdido', antes: 1864, depois: 38 },
        { tipo: 'rpki_invalido_resolvido', antes: 2069, depois: 267 },
        { tipo: 'roa_ganho', antes: 1140, depois: 1135 },
      ],
      inalterados: 'aspa_ganho, rpki_invalido_novo e os demais tipos de evento',
    },
  },
]

/** Notas que afetam algum dos tipos pedidos; lista vazia de tipos (filtro "todos") significa todos os tipos. */
export function notasParaTipos(tipos: string[]): NotaRevisao[] {
  return NOTAS_REVISAO.filter((n) => tipos.length === 0 || tipos.some((t) => n.tipos.includes(t)))
}
