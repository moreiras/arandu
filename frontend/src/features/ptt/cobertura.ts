// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { RsPolCobertura } from '../../types/api'

const n = (v: number) => v.toLocaleString('pt-BR')

/**
 * Regra de leitura da cobertura dos route servers: as leituras vêm de um rodízio diário com orçamento, então parte dos vizinhos foi lida nesta rodada,
 * parte vem de rodadas anteriores (até 35 dias) e parte ainda não foi lida. `lidos + herdados + sem leitura = elegíveis`. Documento sem os campos do
 * rodízio (coleta antiga) cai no "N de M", sem idade: não se inventa data.
 */
export function descreverCobertura(c: RsPolCobertura, alvo: string): string {
  if (c.lidos_na_rodada == null) return `${n(c.coletados)} de ${n(c.elegiveis)} ${alvo} coletados (a idade das leituras não foi registrada neste snapshot)`
  const partes = [`${n(c.lidos_na_rodada)} de ${n(c.elegiveis)} ${alvo} lidos nesta rodada`, `${n(c.herdados)} mantidos de rodadas anteriores`, `${n(c.sem_leitura ?? 0)} sem leitura`]
  const idade = c.idade_max_dias == null ? 'nenhuma leitura disponível' : `leitura mais antiga com ${n(c.idade_max_dias)} ${c.idade_max_dias === 1 ? 'dia' : 'dias'}`
  const lentos = c.pulados_lentos ? `; ${n(c.pulados_lentos)} fora da rodada por route server lento ou com falhas` : ''
  return `${partes.join(', ')} (${idade}${lentos})`
}
