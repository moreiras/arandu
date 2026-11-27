// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** CSV da tabela de participantes do PTT (PT-24). `montarCsvParticipantes` é puro e testado; o download é no navegador, como nos demais CSV do site. */
import type { ParticipantePtt, ParticipantesPtt } from '../../types/api'

const esc = (v: string | number | boolean | null | undefined) => {
  if (v == null) return ''
  const s = String(v)
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
/** `null` (família sem coleta ou ASN fora do Brasil) fica vazio: nunca vira "não". */
const sn = (b: boolean | null) => (b == null ? '' : b ? 'sim' : 'não')

/** IPv6 antes de IPv4 em toda ordem. Nenhum contato (e-mail, telefone) entra: a rota não os traz. */
export const CABECALHO_PARTICIPANTES = [
  'asn', 'nome', 'uf', 'membro_cadastro', 'direto_v6', 'direto_v4', 'originador_v6', 'originador_v4',
  'sessoes_rs', 'sessoes_rs_up', 'sessoes_rs_down', 'rotas_filtradas', 'rotas_recebidas', 'pct_filtradas',
  'rejeicao_por_motivo_rotas', 'rejeicao_por_motivo_idade_dias', 'rejeicao_por_motivo_herdada',
  'acessos_fixos_sici', 'acessos_fixos_sici_compartilhado', 'acessos_fixos_sici_mes_referencia',
  'cdns', 'data_snapshot',
]

export function montarCsvParticipantes(items: ParticipantePtt[], fontes: ParticipantesPtt['fontes'], snapshot: string): string {
  const linhas = items.map((l) => [
    l.asn, l.nome ?? '', l.uf ?? '', sn(l.membro), sn(l.direto.v6), sn(l.direto.v4), sn(l.originador.v6), sn(l.originador.v4),
    l.sessao_rs?.sessoes, l.sessao_rs?.up, l.sessao_rs?.down, l.rejeicao?.filtradas, l.rejeicao?.recebidas, l.rejeicao?.pct,
    l.rejeicao_detalhe?.rotas, l.rejeicao_detalhe?.idade_dias, l.rejeicao_detalhe ? sn(l.rejeicao_detalhe.herdado) : '',
    l.sici?.acessos, l.sici ? sn(l.sici.compartilhado) : '', l.sici ? (fontes.sici.mes_referencia ?? '') : '',
    l.cdns.join(' '), snapshot,
  ].map(esc).join(','))
  return '﻿' + [CABECALHO_PARTICIPANTES.join(','), ...linhas].join('\n')
}

export function baixarCsvParticipantes(texto: string, code: string, snapshot: string) {
  const blob = new Blob([texto], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `participantes-${code}-${snapshot}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
