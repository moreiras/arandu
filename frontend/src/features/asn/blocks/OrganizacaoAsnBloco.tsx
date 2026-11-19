// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const data = (iso: string | null | undefined) => (iso ? iso.slice(0, 10) : '—')

/**
 * Organização do AS segundo o CAIDA e contagem de servidores C2 do Feodo Tracker em prefixos do AS.
 * A organização é inferida pelo CAIDA a partir do WHOIS: não é o grupo societário. O abuso é contagem de terceiros na data da coleta; "nenhum na lista" não quer dizer rede limpa.
 */
export function OrganizacaoAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const org = dados.organizacao
  const ab = dados.abuso
  return (
    <div className="space-y-3 text-sm" data-testid="organizacao-asn">
      {org && (
        <div>
          <p>
            <span className="font-medium">{org.org_nome ?? '—'}</span>
            {org.org_pais ? <span className="text-gray-500"> ({org.org_pais})</span> : null}
            <span className="text-xs text-gray-500"> · {n(org.membros_total)} ASN(s) no mundo</span>
          </p>
          {org.irmaos_br && org.irmaos_br.length > 0 ? (
            <p className="text-xs text-gray-600" data-testid="irmaos">
              Outros ASNs do Brasil da mesma organização:{' '}
              {org.irmaos_br.slice(0, 20).map((a, i) => (
                <span key={a}>{i > 0 ? ', ' : ''}<Link to={`/asn/${a}`} className="text-primario-600 hover:underline">AS{a}</Link></span>
              ))}
              {org.irmaos_br.length > 20 ? ` e mais ${n(org.irmaos_br.length - 20)}` : ''}
            </p>
          ) : (
            <p className="text-xs text-gray-600">Nenhum outro ASN do Brasil nesta organização.</p>
          )}
          <p className="text-xs text-gray-500">{org.limites}</p>
          <p className="text-xs text-gray-400">Fonte: {org.fonte.citacao ?? org.fonte.nome}. Coletado em {data(org.coletado_em)}.</p>
        </div>
      )}
      {ab && (
        <div>
          <p>
            Servidores C2 de botnets (Feodo Tracker) neste AS: <span className="font-medium tabular-nums">{n(ab.feodo_c2)}</span>
            {ab.feodo_c2 > 0 ? ` (${n(ab.feodo_c2_online)} online)` : ' (nenhum na lista)'}
          </p>
          <p className="text-xs text-gray-500">{ab.limites}</p>
          <p className="text-xs text-gray-400">Fonte: {ab.fonte.nome}{ab.fonte.licenca ? `, ${ab.fonte.licenca}` : ''}. Coletado em {data(ab.coletado_em)}.</p>
        </div>
      )}
    </div>
  )
}
