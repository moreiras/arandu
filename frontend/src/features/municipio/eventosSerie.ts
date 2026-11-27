// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { SerieMercadoMunicipio } from '../../types/api'

export interface EventoSerie { indice: number; mes: string; cnpj: string; empresa: string; tipo: 'sem_declaracao' | 'declarou_de_novo'; texto: string }

/**
 * Eventos de declaração lidos da própria série (PT-26, MUN 5.1 c): mês em que um CNPJ da série passa a não ter declaração (ponto vazio com o
 * município presente no mês) e mês em que volta a constar. Só fato observado, sem causa: ponto vazio por mês ausente do cache (município sem
 * acessos no mês) não gera evento. A mesma lista alimenta as marcas do gráfico e a coluna "Evento" da tabela.
 */
export function eventosDaSerie(s: SerieMercadoMunicipio): EventoSerie[] {
  const out: EventoSerie[] = []
  for (let i = 1; i < s.meses.length; i++) {
    if (s.acessos[i] == null) continue
    for (const l of s.lideres) {
      const nome = l.empresa || `CNPJ ${l.cnpj}`
      const antes = l.share[i - 1], agora = l.share[i]
      if (antes != null && agora == null) out.push({ indice: i, mes: s.meses[i], cnpj: l.cnpj, empresa: nome, tipo: 'sem_declaracao', texto: `${nome}: sem declaração em ${s.meses[i]}` })
      else if (antes == null && agora != null && s.acessos[i - 1] != null) out.push({ indice: i, mes: s.meses[i], cnpj: l.cnpj, empresa: nome, tipo: 'declarou_de_novo', texto: `${nome}: declaração volta a constar em ${s.meses[i]}` })
    }
  }
  return out
}
