// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

/**
 * Segurança de roteamento do ASN. ROV e DNSSEC são MEDIÇÕES do APNIC por amostragem (alto = a rede valida), não declarações da rede; o AS Rank é inferência
 * do CAIDA; "prefixo em bogon" é um fato contra as listas da IANA e do Team Cymru (na data da lista). Cada número traz a fonte, a janela e a amostra.
 */
export function SegurancaBloco({ dados }: BlocoProps<AsnCtx>) {
  const s = dados.seguranca!
  const f = s.fontes
  return (
    <div className="space-y-3 text-sm" data-testid="seguranca">
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {s.rov && (
          <div><dt className="text-xs text-gray-500">Validação RPKI medida (APNIC, {f.rov.janela_dias} dias até {f.rov.as_of})</dt>
            <dd className="text-lg font-semibold tabular-nums">{pct(s.rov.validates_pct)}</dd>
            <dd className="text-xs text-gray-500">{n(s.rov.amostras)} amostras{s.rov.amostras < s.parametros.min_amostras ? ' (poucas: valor instável)' : ''}</dd></div>
        )}
        {s.dnssec && (
          <div><dt className="text-xs text-gray-500">Clientes que validam DNSSEC (APNIC, {f.dnssec.janela_dias} dia até {f.dnssec.as_of})</dt>
            <dd className="text-lg font-semibold tabular-nums">{pct(s.dnssec.validates_pct)}</dd>
            <dd className="text-xs text-gray-500">parcial: {pct(s.dnssec.parcial_pct)} · {n(s.dnssec.amostras)} amostras{s.dnssec.amostras < s.parametros.min_amostras ? ' (poucas: valor instável)' : ''}</dd></div>
        )}
        {s.asrank?.rank != null && (
          <div><dt className="text-xs text-gray-500">Posição no AS Rank (CAIDA, estimativa)</dt>
            <dd className="text-lg font-semibold tabular-nums">{n(s.asrank.rank)}º</dd>
            <dd className="text-xs text-gray-500">cone de {n(s.asrank.cone?.asns)} ASNs · {n(s.asrank.grau?.cliente)} clientes, {n(s.asrank.grau?.par)} pares, {n(s.asrank.grau?.provedor)} provedores</dd></div>
        )}
        {(s.n_prefixos_bogon ?? 0) > 0 && (
          <div><dt className="text-xs text-gray-500">Prefixos originados em espaço bogon</dt>
            <dd className="text-lg font-semibold tabular-nums">{n(s.n_prefixos_bogon)}</dd></div>
        )}
      </dl>
      {s.prefixos_em_bogon && s.prefixos_em_bogon.length > 0 && (
        <p className="text-xs text-gray-600">
          Dentro de espaço {s.prefixos_em_bogon.some((b) => b.lista === 'iana') ? 'reservado pela IANA' : ''}{s.prefixos_em_bogon.some((b) => b.lista === 'iana') && s.prefixos_em_bogon.some((b) => b.lista === 'cymru') ? ' ou ' : ''}{s.prefixos_em_bogon.some((b) => b.lista === 'cymru') ? `não alocado (lista do Team Cymru de ${f.bogons.lista_cymru_em})` : ''}:{' '}
          {s.prefixos_em_bogon.map((b) => b.prefixo).join(', ')}{(s.n_prefixos_bogon ?? 0) > s.prefixos_em_bogon.length ? ` e mais ${(s.n_prefixos_bogon ?? 0) - s.prefixos_em_bogon.length}` : ''}.
        </p>
      )}
      {s.asn_reservado && <p className="text-xs text-gray-600">Número de AS em faixa reservada: {s.asn_reservado}.</p>}
      <p className="text-xs text-gray-500">{s.limites}</p>
      <p className="text-xs text-gray-400">Fontes: {f.rov.fonte}; {f.dnssec.fonte}; {f.asrank.citacao ?? f.asrank.fonte}; {f.bogons.fonte}.</p>
    </div>
  )
}
