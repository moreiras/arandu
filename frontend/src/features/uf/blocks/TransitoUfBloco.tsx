// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'

const pct = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`)
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))

/**
 * Provedores de trânsito inferidos dos ASNs com sede na UF: quantos têm provedor inferido (nível provável ou superior), a participação dos maiores e o HHI.
 * É inferência (ARC v2) sobre rotas observadas, não contrato nem tráfego; a UF é a da sede da organização; usuários são estimativa APNIC.
 */
export function TransitoUfBloco({ dados }: BlocoProps<UfCtx>) {
  const t = dados.transito
  if (!t) return null
  return (
    <div className="space-y-2 text-sm" data-testid="transito-uf">
      <p>
        <span className="tabular-nums font-medium">{n(t.asns_com_provedor)}</span> de <span className="tabular-nums">{n(t.asns_br)}</span> ASNs com sede na UF têm provedor inferido ({t.pct_com_provedor.toLocaleString('pt-BR')}%) ·{' '}
        {n(t.provedores_distintos)} provedores distintos · maior provedor {pct(t.top1_share)}, três maiores {pct(t.top3_share)} ·{' '}
        <span title="Índice Herfindahl-Hirschman da participação de cada provedor nos pares (ASN da UF, provedor), de 0 a 10.000">HHI {n(t.hhi_clientes)}</span> · provedores estrangeiros {pct(t.share_provedores_estrangeiros)}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b">
              <th className="px-2 py-1">Provedor inferido</th>
              <th className="px-2 py-1 text-right">ASNs da UF</th>
              <th className="px-2 py-1 text-right">Participação</th>
              <th className="px-2 py-1 text-right" title="Estimativa APNIC; repete-se entre ASNs da mesma operadora">Usuários (estim.)</th>
            </tr>
          </thead>
          <tbody>
            {t.provedores.slice(0, 10).map((p) => (
              <tr key={p.asn} className="border-b border-gray-50">
                <td className="px-2 py-1"><Link to={`/asn/${p.asn}`} className="text-primario-700 hover:underline">AS{p.asn}</Link> <span className="text-gray-600">{p.nome ?? ''}</span>{!p.br && <span className="text-xs text-gray-400"> · exterior</span>}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(p.clientes_uf)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{pct(p.share_clientes)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(p.usuarios_uf)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">{t.limites}</p>
      <p className="text-xs text-gray-400">Inferência (ARC v2) no snapshot {t.snapshot_date}; só relações de nível provável ou superior.</p>
    </div>
  )
}
