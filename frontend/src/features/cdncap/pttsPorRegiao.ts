// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { CDNPresenceResponse, IXPIndexEntry } from '../../types/api'
import { REGIOES } from '../../lib/ufs'

/** Uma linha da tabela "Por PTT": um PTT do IX.br, com o que o catálogo de CDNs mostra nele. */
export interface LinhaPtt {
  code: string
  nome: string
  uf: string | null
  /** Participantes do cadastro do IX.br; nulo sem a lista de PTTs. */
  membros: number | null
  /** Provedores do catálogo que constam do cadastro de participantes do PTT. */
  cdnsMembro: number
  /** Dos provedores membro, os que têm sessão no route server (coleta válida). */
  comRouteServer: number
  /** Provedores do catálogo não membros, com prefixos vistos no PTT por outro participante (inferido). */
  soViaOutroAs: number
}

export interface GrupoRegiao {
  id: string
  nome: string
  ptts: LinhaPtt[]
  /** UFs da região com PTT, mas sem nenhum PTT local com provedor do catálogo. */
  ufsSemCdn: string[]
}

/**
 * "Por PTT" agrupado por região e UF (PT-22 / cdns 5.2): cada PTT do IX.br com membros, provedores do catálogo e o estado deles, calculado das linhas de
 * `/cdns/presence` (nada digitado à mão) e da lista de PTTs (`/ixps`) para a UF e o total de membros. Sem ranking: a ordem é a da região do IBGE, da UF e do código
 * do PTT. Zero quer dizer nenhum provedor do catálogo, que é curado e incompleto. PTT sem UF no índice vai para "UF não informada".
 */
export function pttsPorRegiao(d: CDNPresenceResponse | null | undefined, ixps: IXPIndexEntry[] | undefined): GrupoRegiao[] {
  if (!d) return []
  const indice = new Map((ixps ?? []).map((i) => [i.code, i]))
  const linhas: LinhaPtt[] = d.ixbr_columns.map((col) => ({
    code: col.code, nome: indice.get(col.code)?.name ?? col.name, uf: indice.get(col.code)?.uf || null, membros: indice.get(col.code)?.ixbr_members_count ?? null,
    cdnsMembro: d.cdns.filter((c) => c.ixbr.includes(col.code)).length,
    comRouteServer: d.cdns.filter((c) => c.ixbr_rs?.includes(col.code)).length,
    soViaOutroAs: d.cdns.filter((c) => c.ixbr_origem?.includes(col.code)).length,
  }))
  const ordem = (a: LinhaPtt, b: LinhaPtt) => (a.uf ?? '~').localeCompare(b.uf ?? '~') || a.code.localeCompare(b.code)
  const grupos: GrupoRegiao[] = REGIOES.map((r) => {
    const ptts = linhas.filter((l) => l.uf != null && r.ufs.includes(l.uf)).sort(ordem)
    const ufsComPtt = [...new Set(ptts.map((p) => p.uf as string))]
    return { id: r.id, nome: r.nome, ptts, ufsSemCdn: ufsComPtt.filter((uf) => ptts.filter((p) => p.uf === uf).every((p) => p.cdnsMembro === 0)).sort() }
  })
  const sem = linhas.filter((l) => l.uf == null || !REGIOES.some((r) => r.ufs.includes(l.uf as string))).sort(ordem)
  if (sem.length > 0) grupos.push({ id: 'sem-uf', nome: 'UF não informada', ptts: sem, ufsSemCdn: [] })
  return grupos.filter((g) => g.ptts.length > 0)
}
