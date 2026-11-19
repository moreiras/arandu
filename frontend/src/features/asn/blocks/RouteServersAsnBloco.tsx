// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { DICA_PREFIXOS_LIMITE } from '../../../lib/textos'
import { Dica } from '../../../components/ui/Dica'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const data = (iso: string | null | undefined) => (iso ? iso.slice(0, 16).replace('T', ' ') + ' UTC' : '—')

/**
 * Sessões do ASN nos route servers do IX.br, por PTT. É o que o route server mostra na data da coleta: sessão down não diz de quem é a causa,
 * e o motivo é o que o Alice reporta. Sessão em route server sem frescor confirmado (cache de vizinhos do Alice velho) vem marcada como incerta.
 */
export function RouteServersAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const rs = dados.routeServers!
  const ptts = Object.entries(rs.ixps).sort(([a], [b]) => a.localeCompare(b))
  return (
    <div className="space-y-3 text-sm" data-testid="route-servers-asn">
      <p className="text-xs text-gray-600">
        {n(rs.total.sessoes)} sessões em {n(rs.total.ixps)} PTT(s): {n(rs.total.up)} up e {n(rs.total.down)} down.
      </p>
      <table className="min-w-full text-xs">
        <thead className="text-gray-500"><tr>
          <th className="text-left px-2 py-1">PTT</th><th className="text-right px-2 py-1">Sessões up</th><th className="text-right px-2 py-1">Down</th>
          <th className="text-right px-2 py-1">Maior tempo de queda (dias)</th><th className="text-right px-2 py-1">Prefixos / limite<Dica texto={DICA_PREFIXOS_LIMITE} rotulo="Prefixos / limite" /></th><th className="text-left px-2 py-1">Cadastro</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {ptts.map(([code, x]) => (
            <tr key={code}>
              <td className="px-2 py-1"><Link to={`/ixp/${code}`} className="text-primario-600 hover:underline">{code.toUpperCase()}</Link></td>
              <td className="px-2 py-1 text-right tabular-nums">{n(x.up)} de {n(x.sessoes)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{n(x.down)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{x.max_dias_down != null ? n(x.max_dias_down) : '—'}</td>
              <td className="px-2 py-1 text-right tabular-nums">{x.max_uso_limite != null ? `${Math.round(x.max_uso_limite * 100)}%` : '—'}</td>
              <td className="px-2 py-1">{x.cadastrado ? 'cadastrado' : 'sem cadastro no IX.br'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <details className="text-xs text-gray-600">
        <summary className="cursor-pointer">Cada sessão</summary>
        <table className="min-w-full mt-1">
          <thead className="text-gray-500"><tr>
            <th className="text-left px-2 py-1">Route server</th><th className="text-left px-2 py-1">IP do par</th><th className="text-left px-2 py-1">Estado</th>
            <th className="text-right px-2 py-1">Dias no estado</th><th className="text-right px-2 py-1">Recebidas / limite</th><th className="text-left px-2 py-1">Último erro</th>
          </tr></thead>
          <tbody className="divide-y divide-gray-100">
            {ptts.flatMap(([code, x]) => x.lista.map((s) => (
              <tr key={`${code}-${s.rs}-${s.ip}`}>
                <td className="px-2 py-1 font-mono">{s.rs}</td>
                <td className="px-2 py-1 font-mono">{s.ip}</td>
                <td className="px-2 py-1">{s.estado === 'up' ? 'up' : 'down'}{s.rs_incerto ? ' (sem frescor confirmado: incerta)' : ''}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(s.dias)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(s.recebidas)} / {n(s.limite)}</td>
                <td className="px-2 py-1">{s.erro || '—'}</td>
              </tr>
            )))}
          </tbody>
        </table>
      </details>
      <p className="text-xs text-gray-500">{rs.limites}</p>
      <p className="text-xs text-gray-400">Fonte: {rs.fonte ?? 'Looking Glass do IX.br (Alice-LG)'}{rs.versao_alice ? ` ${rs.versao_alice}` : ''}; cadastro de membros do IX.br. Coletado em {data(rs.coletado_em)}.</p>
    </div>
  )
}
