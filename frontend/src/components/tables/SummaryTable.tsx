import type { GlobalTableStats, IXPAggregateStats } from '../../types/api'
import { Dica } from '../ui/Dica'

interface SummaryTableProps {
  globalTable: GlobalTableStats
  ixpAggregate: IXPAggregateStats
  totalBrASNs?: number
  /** Total de PTTs do snapshot (ok + parcial + ausente); sem ele o rótulo não traz número. */
  totalIxps?: number
}

function num(v: number | undefined | null, decimals = 0): string {
  if (v == null) return '—'
  return v.toLocaleString('pt-BR', { maximumFractionDigits: decimals })
}

function pct(v: number | undefined | null, decimals = 1): string {
  if (v == null) return '—'
  return `${v.toFixed(decimals)}%`
}

function Th({ label, tooltip, className = '' }: { label: string; tooltip: string; className?: string }) {
  return (
    <th scope="col" className={`px-2 py-1.5 text-right align-bottom font-medium leading-tight max-w-[8rem] ${className}`}>
      <Dica texto={tooltip}>{label}</Dica>
    </th>
  )
}

export function SummaryTable({ globalTable, ixpAggregate, totalBrASNs, totalIxps }: SummaryTableProps) {
  const brAsnCovPct =
    totalBrASNs && ixpAggregate.br_asns_origin_union_count
      ? (ixpAggregate.br_asns_origin_union_count / totalBrASNs) * 100
      : null
  const ftAsnCovPct =
    globalTable.total_asns && ixpAggregate.asn_origin_union_count != null
      ? (ixpAggregate.asn_origin_union_count / globalTable.total_asns) * 100
      : null
  const ftRowBrAsnCovPct =
    totalBrASNs && globalTable.br_asns_in_ft != null
      ? (globalTable.br_asns_in_ft / totalBrASNs) * 100
      : null

  const ftRowAsnPbrPct =
    globalTable.br_asns_in_ft != null && globalTable.total_asns > 0
      ? (globalTable.br_asns_in_ft / globalTable.total_asns) * 100
      : null

  const thBase = 'px-2 py-1.5 text-right font-medium whitespace-nowrap'
  const thBorderL = `${thBase} border-l border-gray-200`

  return (
    <div className="space-y-3">
      <h2 className="text-base font-semibold text-gray-800">Agregado do IX.br e tabela global</h2>

      {/* ── Tabela 1: Tabela global ── */}
      <div className="overflow-x-auto rounded border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr className="border-b border-gray-200">
              <th className="px-2 py-1.5 text-left font-semibold text-gray-500 sticky left-0 bg-gray-50 whitespace-nowrap">
                Tabela Global
              </th>
              <th colSpan={3} className="px-2 py-1.5 text-center font-semibold text-gray-400 border-l border-gray-200">AS</th>
              <th colSpan={4} className="px-2 py-1.5 text-center font-semibold text-v6-400 border-l border-gray-200">IPv6</th>
              <th colSpan={4} className="px-2 py-1.5 text-center font-semibold text-primario-400 border-l border-gray-200">IPv4</th>
            </tr>
            <tr>
              <th className="px-2 py-1.5 sticky left-0 bg-gray-50" />
              {/* AS */}
              <Th label="Originadores" tooltip="Total de ASNs únicos originando prefixos na tabela de roteamento global" className={thBorderL} />
              <Th label="Cobertura Registro.br" tooltip="% dos ASNs brasileiros (Registro.br) com ao menos um prefixo visível na tabela global" className={thBase} />
              <Th label="Parte do Brasil" tooltip="% dos ASNs da tabela global que são brasileiros (Registro.br): ASNs BR visíveis dividido pelo total de ASNs" className={thBase} />
              {/* IPv6 */}
              <Th label="Prefixos" tooltip="Total de prefixos IPv6 únicos presentes na tabela de roteamento global" className={thBorderL} />
              <Th label="/48s" tooltip="Espaço IPv6 total na tabela global, expresso em equivalentes /48" className={thBase} />
              <Th label="Cobertura Registro.br" tooltip="% do espaço IPv6 alocado ao Brasil (Registro.br) visível na tabela global, calculado como rir_br_visible / rir_br" className={thBase} />
              <Th label="Parte do Brasil" tooltip="% do espaço total IPv6 da tabela global que é alocado ao Brasil (Registro.br), calculado como rir_br_visible / global_all" className={thBase} />
              {/* IPv4 */}
              <Th label="Prefixos" tooltip="Total de prefixos IPv4 únicos presentes na tabela de roteamento global" className={thBorderL} />
              <Th label="/24s" tooltip="Espaço IPv4 total na tabela global, expresso em equivalentes /24" className={thBase} />
              <Th label="Cobertura Registro.br" tooltip="% do espaço IPv4 alocado ao Brasil (Registro.br) visível na tabela global, calculado como rir_br_visible / rir_br" className={thBase} />
              <Th label="Parte do Brasil" tooltip="% do espaço total IPv4 da tabela global que é alocado ao Brasil (Registro.br), calculado como rir_br_visible / global_all" className={thBase} />
            </tr>
          </thead>
          <tbody className="text-sm">
            <tr className="bg-gray-50/60">
              <td className="px-2 py-2 text-gray-500 text-xs sticky left-0 bg-gray-50/60 whitespace-nowrap">
                RouteViews
              </td>
              {/* AS */}
              <td className="px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">{num(globalTable.total_asns)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(ftRowBrAsnCovPct)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(ftRowAsnPbrPct)}</td>
              {/* IPv6 */}
              <td className="px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">{num(globalTable.v6_prefixes)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{num(globalTable.v6_space_48, 0)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(globalTable.v6_br_coverage_pct)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(globalTable.v6_br_pct_of_ft)}</td>
              {/* IPv4 */}
              <td className="px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">{num(globalTable.v4_prefixes)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{num(globalTable.v4_space_24)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(globalTable.v4_br_coverage_pct)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(globalTable.v4_br_pct_of_ft)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Tabela 2: Agregado IX.br ── */}
      <div className="overflow-x-auto rounded border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-primario-50/40 text-xs text-gray-500 uppercase">
            <tr className="border-b border-gray-200">
              <th className="px-2 py-1.5 text-left font-semibold text-primario-600/80 sticky left-0 bg-primario-50/40 whitespace-nowrap">
                Agregado IX.br
              </th>
              <th colSpan={4} className="px-2 py-1.5 text-center font-semibold text-gray-400 border-l border-gray-200">AS</th>
              <th colSpan={4} className="px-2 py-1.5 text-center font-semibold text-v6-400 border-l border-gray-200">IPv6</th>
              <th colSpan={4} className="px-2 py-1.5 text-center font-semibold text-primario-400 border-l border-gray-200">IPv4</th>
            </tr>
            <tr>
              <th className="px-2 py-1.5 sticky left-0 bg-primario-50/40" />
              {/* AS */}
              <Th label="Diretos no RS" tooltip="ASNs com sessão com route server em algum PTT do IX.br (união de IPv6 e IPv4, sem repetição)" className={thBorderL} />
              <Th label="Originadores" tooltip="ASNs originando prefixos em qualquer IXP do IX.br (união de IPv6 e IPv4, sem repetição)" className={thBase} />
              <Th label="Cobertura Registro.br" tooltip="% dos ASNs brasileiros (Registro.br) que originam prefixos em algum IXP do IX.br" className={thBase} />
              <Th label="Cobertura tabela global" tooltip="% dos ASNs da tabela global que originam prefixos em algum IXP do IX.br" className={thBase} />
              {/* IPv6 */}
              <Th label="Prefixos" tooltip="Total de prefixos IPv6 únicos visíveis na união de todos os IXPs do IX.br" className={thBorderL} />
              <Th label="/48s" tooltip="Espaço IPv6 coberto pela união dos IXPs, em equivalentes /48" className={thBase} />
              <Th label="Cobertura Registro.br" tooltip="% do espaço IPv6 alocado ao Brasil (Registro.br) visível na união dos IXPs do IX.br" className={thBase} />
              <Th label="Cobertura tabela global" tooltip="% do espaço IPv6 da tabela global coberto pela união dos IXPs do IX.br" className={thBase} />
              {/* IPv4 */}
              <Th label="Prefixos" tooltip="Total de prefixos IPv4 únicos visíveis na união de todos os IXPs do IX.br" className={thBorderL} />
              <Th label="/24s" tooltip="Espaço IPv4 coberto pela união dos IXPs, em equivalentes /24" className={thBase} />
              <Th label="Cobertura Registro.br" tooltip="% do espaço IPv4 alocado ao Brasil (Registro.br) visível na união dos IXPs do IX.br" className={thBase} />
              <Th label="Cobertura tabela global" tooltip="% do espaço IPv4 da tabela global coberto pela união dos IXPs do IX.br" className={thBase} />
            </tr>
          </thead>
          <tbody className="text-sm">
            <tr className="bg-primario-50/20">
              <td className="px-2 py-2 text-gray-500 text-xs sticky left-0 bg-primario-50/20 whitespace-nowrap">
                {totalIxps ? `${totalIxps} IXPs` : 'IXPs do IX.br'}
              </td>
              {/* AS */}
              <td className="px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">{num(ixpAggregate.asn_direct_union_count)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{num(ixpAggregate.asn_origin_union_count)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{brAsnCovPct != null ? pct(brAsnCovPct) : '—'}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{ftAsnCovPct != null ? pct(ftAsnCovPct) : '—'}</td>
              {/* IPv6 */}
              <td className="px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">{num(ixpAggregate.v6_prefixes)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{num(ixpAggregate.v6_space_48, 0)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(ixpAggregate.v6_br_coverage_pct)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(ixpAggregate.v6_coverage_pct)}</td>
              {/* IPv4 */}
              <td className="px-2 py-2 text-right tabular-nums text-gray-700 border-l border-gray-100">{num(ixpAggregate.v4_prefixes)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{num(ixpAggregate.v4_space_24)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(ixpAggregate.v4_br_coverage_pct)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-gray-700">{pct(ixpAggregate.v4_coverage_pct)}</td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  )
}
