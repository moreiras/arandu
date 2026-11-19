// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../../components/entidade'
import type { ASNDocument, ReferenciasAsn } from '../../types/api'
import { SITE } from '../../lib/site'

/**
 * Frase-síntese do AS: gerada por **regras**, sem modelo de linguagem. Cada frase sai de campos do snapshot, leva o
 * selo (fato, inferido ou estimado) e a versão das regras. Mudar uma regra muda `REGRAS_VERSAO`; o teste fixa o conjunto de ids.
 */
export const REGRAS_VERSAO = 'sintese-as-1'

export interface Frase { id: string; texto: string; selo: Selo }

const n = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const plural = (q: number, um: string, varios: string) => `${n(q)} ${q === 1 ? um : varios}`

/** As frases do AS, na ordem de leitura; regra sem dado não gera frase (nunca preenche com palpite). */
export function sinteseAs(doc: ASNDocument, ref?: ReferenciasAsn | null): Frase[] {
  const f: Frase[] = []
  const v4 = doc.global_prefixes_v4_count ?? doc.global_prefixes_v4?.length ?? 0
  const v6 = doc.global_prefixes_v6_count ?? doc.global_prefixes_v6?.length ?? 0
  f.push({
    id: 'anuncio', selo: 'fato',
    texto: v4 + v6 > 0
      ? `AS${doc.asn} (${doc.name}) anuncia ${plural(v6, 'prefixo IPv6', 'prefixos IPv6')} e ${plural(v4, 'prefixo IPv4', 'prefixos IPv4')} na tabela de roteamento global.`
      : `AS${doc.asn} (${doc.name}) não aparece com prefixos na tabela de roteamento global neste snapshot.`,
  })
  const diretos = doc.ixps_direct?.length ?? 0
  const origem = doc.ixps_origin?.length ?? 0
  f.push({
    id: 'ptts', selo: 'fato',
    texto: diretos + origem > 0
      ? `Está em ${plural(diretos, 'PTT do IX.br', 'PTTs do IX.br')} com sessão direta e aparece como originador em ${plural(origem, 'PTT', 'PTTs')}.`
      : 'Não aparece em PTTs do IX.br coletados neste snapshot.',
  })
  const rpki = Object.values(doc.rpki_validation ?? {})
  if (rpki.length > 0) {
    const valido = rpki.filter((s) => s === 'valid').length
    const invalido = rpki.filter((s) => s === 'invalid').length
    f.push({
      id: 'rpki', selo: 'fato',
      texto: `${n(valido)} de ${n(rpki.length)} ${rpki.length === 1 ? 'prefixo anunciado tem' : 'prefixos anunciados têm'} ROA válido`
        + (invalido > 0 ? `; ${plural(invalido, 'está inválido', 'estão inválidos')}.` : '.'),
    })
  }
  if (doc.apnic_users != null && doc.apnic_users > 0) {
    const pos = ref?.usuarios_posicao
    f.push({
      id: 'usuarios', selo: 'estimado',
      texto: `Estimativa do APNIC: cerca de ${n(doc.apnic_users)} usuários`
        + (pos && ref ? ` (${n(pos)}º entre ${n(ref.usuarios_com_dado)} ASes brasileiros com estimativa).` : '.'),
    })
  }
  if (doc.single_upstream_v4 != null) {
    f.push({ id: 'transito', selo: 'inferido', texto: `Pelas rotas observadas, usa um único provedor de trânsito IPv4 (AS${doc.single_upstream_v4}).` })
  } else if (doc.is_multihomed_v4) {
    f.push({ id: 'transito', selo: 'inferido', texto: 'Pelas rotas observadas, usa mais de um provedor de trânsito IPv4.' })
  }
  const alertas = doc.alerts?.length ?? 0
  if (alertas > 0) f.push({ id: 'alertas', selo: 'fato', texto: `${plural(alertas, 'ponto de atenção', 'pontos de atenção')} nas regras do ${SITE.nome} (aba Resumo).` })
  return f
}

export interface KpiAs { id: string; rotulo: string; valor: number | null; sufixo?: string; referencia?: string }

/** Indicadores da ficha, cada um com a referência de comparação quando o servidor a envia (`include=referencias`). */
export function kpisAs(doc: ASNDocument, ref?: ReferenciasAsn | null): KpiAs[] {
  const med = (v?: number | null, un = '') => (v == null ? undefined : `mediana dos ASes BR: ${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}${un}`)
  return [
    { id: 'v6', rotulo: 'Prefixos IPv6 anunciados', valor: doc.global_prefixes_v6_count ?? null },
    { id: 'v4', rotulo: 'Prefixos IPv4 anunciados', valor: doc.global_prefixes_v4_count ?? null, referencia: med(ref?.prefixos_v4_mediana) },
    { id: 'ptts', rotulo: 'PTTs com sessão direta', valor: doc.ixps_direct?.length ?? null, referencia: med(ref?.ixps_diretos_mediana) },
    { id: 'usuarios', rotulo: 'Usuários estimados (APNIC)', valor: doc.apnic_users ?? null,
      referencia: ref?.usuarios_posicao ? `${ref.usuarios_posicao.toLocaleString('pt-BR')}º de ${ref.usuarios_com_dado.toLocaleString('pt-BR')} ASes BR` : undefined },
    { id: 'v6usuarios', rotulo: 'Usuários IPv6', valor: doc.apnic_v6_pct_as ?? null, sufixo: '%', referencia: med(ref?.pct_v6_mediana, '%') },
  ]
}
