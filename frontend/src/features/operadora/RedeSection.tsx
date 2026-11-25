// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useId, useState } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import type { OperadoraRede } from '../../types/api'
import { KPI, fmt } from './ui'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../lib/ordenacao'

export const SEVERITY_LABEL: Record<string, string> = { critico: 'Crítico', aviso: 'Aviso', info: 'Info' }
export const SEVERITY_CLS: Record<string, string> = {
  critico: 'bg-perigo-100 text-perigo-700',
  aviso: 'bg-aviso-100 text-aviso-700',
  info: 'bg-gray-100 text-gray-500',
}
export const CATEGORY_LABEL: Record<string, string> = {
  roteamento: 'Roteamento', rpki: 'RPKI', v4v6: 'IPv6/IPv4', presenca: 'Presença', geo: 'Geolocalização',
}

/**
 * Seção "Rede": agregação de BGP/RPKI/IX.br/alertas de todos os ASNs do CNPJ.
 * Tabela por-ASN vem colapsada — operadoras com dezenas de ASNs (ex: Vero, 36)
 * não devem abrir com uma tabela enorme por padrão.
 */
export function RedeSection({ rede }: { rede: OperadoraRede }) {
  const [showAsns, setShowAsns] = useState(false)
  const idTabela = useId()
  const porRaiz = rede.asns.filter((a) => a.vinculo === 'raiz').length
  const { ordenados, props } = useOrdenacao(rede.asns, {
    asn: { valor: (a) => a.asn, primeiro: 'asc' },
    nome: (a) => a.name || null,
    usuarios: (a) => a.apnic_users,
    v6: (a) => a.rir_prefixes_v6_count,
    v4: (a) => a.rir_prefixes_v4_count,
    rpki: { valor: (a) => (a.has_rpki ? 1 : 0), primeiro: 'desc' },
    aspa: { valor: (a) => (a.has_aspa ? 1 : 0), primeiro: 'desc' },
    ixps: (a) => a.ixps_direct_count,
    alertas: (a) => a.alerts_count,
  })
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h2 className="text-base font-semibold text-gray-800 mb-1">
        Rede (BGP · RPKI · IX.br)
      </h2>
      <p className="text-xs text-gray-400 mb-3">
        Agregado de {rede.asn_count} ASN{rede.asn_count !== 1 ? 's' : ''} do Registro.br com este CNPJ
        {porRaiz > 0 && <> ou com outro CNPJ da mesma raiz ({porRaiz} pela raiz, vínculo inferido)</>}.
        Usuários e blocos são somados, cada ASN uma vez; IX.br e RPKI/ASPA são união (basta um ASN ter).
      </p>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 mb-3">
        <KPI label="Usuários (APNIC)" value={fmt(rede.total_apnic_users)} />
        <KPI label="Usuários IPv6" value={fmt(rede.total_apnic_v6_users)} />
        <KPI label="Blocos IPv6 (RIR)" value={fmt(rede.total_rir_prefixes_v6)} />
        <KPI label="Blocos IPv4 (RIR)" value={fmt(rede.total_rir_prefixes_v4)} />
        <KPI label="IXPs (diretos)" value={fmt(rede.ixps_direct.length)}
             hint={rede.ixps_direct.slice(0, 6).join(', ') || undefined} />
        <KPI label="Alertas" value={fmt(rede.alertas.total)} />
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        <span className={`text-xs font-semibold rounded px-1.5 py-0.5 ${rede.has_rpki ? 'bg-ok-100 text-ok-700' : 'bg-gray-100 text-gray-400'}`}>
          {rede.has_rpki ? 'RPKI: ao menos um ASN' : 'RPKI: nenhum ASN'}
        </span>
        <span className={`text-xs font-semibold rounded px-1.5 py-0.5 ${rede.has_aspa ? 'bg-ok-100 text-ok-700' : 'bg-gray-100 text-gray-400'}`}>
          {rede.has_aspa ? 'ASPA: ao menos um ASN' : 'ASPA: nenhum ASN'}
        </span>
      </div>

      {rede.alertas.total > 0 && (
        <div className="mb-3 space-y-1">
          {rede.alertas.por_categoria.map(g => (
            // A lista "AS: alerta" ficava só no title (teclado e toque não alcançam): agora abre no próprio item (details/summary).
            <details key={`${g.category}-${g.severity}`} className="text-xs border border-gray-100 rounded px-2 py-1" data-testid="alerta-categoria">
              <summary className="flex cursor-pointer items-center gap-2">
              <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${SEVERITY_CLS[g.severity] ?? 'bg-gray-100 text-gray-500'}`}>
                {SEVERITY_LABEL[g.severity] ?? g.severity}
              </span>
              <span className="text-gray-600">{CATEGORY_LABEL[g.category] ?? g.category}</span>
              <span className="text-gray-400">·</span>
              <span className="text-gray-500">
                {/* g.count conta alertas e g.asns traz uma entrada por alerta: o mesmo ASN se repetia ("5 ASNs: AS28126, AS28126…"). */}
                {(() => {
                  const asns = [...new Set(g.asns.map(a => a.asn))]
                  return `${g.count} alerta${g.count !== 1 ? 's' : ''} em ${asns.length} ASN${asns.length !== 1 ? 's' : ''}: ${asns.slice(0, 4).map(a => `AS${a}`).join(', ')}${asns.length > 4 ? ` +${asns.length - 4}` : ''}`
                })()}
              </span>
              </summary>
              <ul className="mt-1 space-y-0.5 pl-2 text-gray-600">
                {g.asns.map((a, i) => <li key={`${a.asn}-${i}`}><Link to={`/asn/${a.asn}`} className="font-mono text-primario-700 hover:underline">AS{a.asn}</Link>: {a.title}</li>)}
              </ul>
            </details>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={() => setShowAsns(s => !s)}
        aria-expanded={showAsns}
        aria-controls={showAsns ? idTabela : undefined}
        className="text-xs text-primario-600 hover:underline"
      >
        {showAsns ? '▾ ocultar' : '▸ ver'} detalhe por ASN ({rede.asns.length})
      </button>

      {showAsns && (
        <div className="mt-2 overflow-x-auto" id={idTabela}>
          <table className="w-full text-xs">
            <caption className="sr-only">Detalhe por ASN do CNPJ</caption>
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-100">
                <ThOrdenavel {...props('asn')} className="px-2 py-1">ASN</ThOrdenavel>
                <ThOrdenavel {...props('nome')} className="px-2 py-1">Nome</ThOrdenavel>
                <ThOrdenavel {...props('usuarios')} alinhar="right" className="px-2 py-1 text-right">Usuários</ThOrdenavel>
                <ThOrdenavel {...props('v6')} alinhar="right" className="px-2 py-1 text-right">Blocos v6</ThOrdenavel>
                <ThOrdenavel {...props('v4')} alinhar="right" className="px-2 py-1 text-right">Blocos v4</ThOrdenavel>
                <ThOrdenavel {...props('rpki')} alinhar="center" className="px-2 py-1 text-center">RPKI</ThOrdenavel>
                <ThOrdenavel {...props('aspa')} alinhar="center" className="px-2 py-1 text-center">ASPA</ThOrdenavel>
                <ThOrdenavel {...props('ixps')} alinhar="right" className="px-2 py-1 text-right">IXPs</ThOrdenavel>
                <ThOrdenavel {...props('alertas')} alinhar="right" className="px-2 py-1 text-right">Alertas</ThOrdenavel>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {ordenados.map(a => (
                <tr key={a.asn} className="hover:bg-gray-50">
                  <td className="px-2 py-1">
                    <Link to={`/asn/${a.asn}`} className="text-primario-600 hover:underline font-mono">AS{a.asn}</Link>
                    {a.vinculo === 'raiz' && <span className="ml-1 text-gray-400">(mesma raiz, inferido)</span>}
                  </td>
                  <td className="px-2 py-1 text-gray-600 truncate max-w-[180px]">{a.name || '—'}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(a.apnic_users)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(a.rir_prefixes_v6_count)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(a.rir_prefixes_v4_count)}</td>
                  <td className="px-2 py-1 text-center">{a.has_rpki ? '✓' : '—'}</td>
                  <td className="px-2 py-1 text-center">{a.has_aspa ? '✓' : '—'}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(a.ixps_direct_count)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(a.alerts_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
