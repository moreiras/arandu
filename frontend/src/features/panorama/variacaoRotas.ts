// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { SerieNacional } from '../../services/api'

const pp = (v: number) => `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} p.p.`

/**
 * Variação do estado RPKI das rotas brasileiras (IPv6 antes de IPv4) entre dois snapshots, na mesma regra de comparabilidade das séries
 * nacionais (`core/comparabilidade.py`, PT-28). Uma família sem variação calculada (medida ausente, base ou método diferentes, cobertura
 * que mudou) fica de fora, nunca como zero; sem nenhuma, não há texto. Cor não expressa juízo: o texto não leva `bom`.
 */
export function variacaoRotasRpki(serie: SerieNacional | undefined, idV6: string, idV4: string, anterior: string | null): { texto: string } | undefined {
  if (!serie || !anterior) return undefined
  const partes: string[] = []
  for (const [rotulo, id] of [['IPv6', idV6], ['IPv4', idV4]] as const) {
    const v = serie.metricas.find((m) => m.id === id)?.variacao
    if (v?.calculada && v.absoluta != null && v.de === anterior) partes.push(`${rotulo} ${pp(v.absoluta)}`)
  }
  return partes.length ? { texto: `${partes.join(' · ')} desde ${anterior} (série semanal)` } : undefined
}
