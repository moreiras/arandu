import { useQuery } from '@tanstack/react-query'
import { Link } from '../layout/LinkDatado'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import { fetchOutorgasStats, fetchAcessosMovelStats } from '../../services/api'
import { somaValores } from '../../lib/acessos'
import { AccessHistoryChart } from '../acessos/AccessHistoryChart'
import { UF_REGION, REGION_ORDER } from '../../utils/regioes'
import type { SiciSeriePoint, SMPStats, SiciMovelStats } from '../../types/api'
import { corLegivel } from '../../lib/contraste'
import { VerDados } from '../ui/VerDados'

const SECTION_COLOR = '#0d9488'
const COLOR_WITH_ASN = '#60a5fa'
const COLOR_WITHOUT_ASN = '#2dd4bf'
const COLOR_PF = '#0ea5e9'
const COLOR_PJ = '#f59e0b'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const fmtPct = (n: number | null | undefined, dec = 1) =>
  n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}%`

function StatCard({ value, label, sub, accent }: { value: string; label: string; sub?: string; accent?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={accent ? { color: corLegivel(accent) } : undefined}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function Barras({ dados, total, limite = 6 }: { dados: Record<string, number>; total: number; limite?: number }) {
  const rows = Object.entries(dados).sort((a, b) => b[1] - a[1]).slice(0, limite)
  return (
    <div className="space-y-1">
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-xs">
          <span className="w-28 truncate text-gray-600" title={k}>{k}</span>
          <span className="flex-1 h-2.5 bg-gray-100 rounded-sm overflow-hidden">
            <span className="block h-full bg-mercado-500/70" style={{ width: `${total ? (100 * v) / total : 0}%` }} />
          </span>
          <span className="w-24 text-right tabular-nums text-gray-500">{fmt(v)}</span>
        </div>
      ))}
    </div>
  )
}

// ── outorgas × acessos por UF/região ────────────────────────────────────────────

function OutorgasPorUf({ smp }: { smp: SMPStats }) {
  const ufData = (smp.uf_breakdown ?? []).slice(0, 16)
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Outorgas SMP por UF (com/sem ASN)</div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={ufData} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis dataKey="uf" tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip formatter={(v: number, name: string) => [fmt(v), name === 'with_asn' ? 'Com ASN' : 'Sem ASN']}
                   labelFormatter={(l) => `UF: ${l}`} />
          <Legend formatter={(v) => (v === 'with_asn' ? 'Com ASN' : 'Sem ASN')} wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="with_asn" stackId="a" fill={COLOR_WITH_ASN} />
          <Bar dataKey="without_asn" stackId="a" fill={COLOR_WITHOUT_ASN} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={ufData as unknown as Record<string, unknown>[]} />
    </div>
  )
}

function AcessosPorRegiao({ acessos }: { acessos: SiciMovelStats }) {
  const agg: Record<string, { pf: number; pj: number }> = {}
  for (const [uf, porTipo] of Object.entries(acessos.distrib_modalidade ?? {})) {
    const r = UF_REGION[uf] ?? '—'
    const a = agg[r] ?? { pf: 0, pj: 0 }
    a.pf += Object.values(porTipo.pf ?? {}).reduce((s, v) => s + v, 0)
    a.pj += Object.values(porTipo.pj ?? {}).reduce((s, v) => s + v, 0)
    agg[r] = a
  }
  const data = REGION_ORDER.filter(r => agg[r]).map(r => ({ region: r, ...agg[r] }))
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500 mb-2 font-medium">Acessos móveis declarados (SICI) por macrorregião</div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 12, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={86} />
          <Tooltip formatter={(v: number, name: string) => [fmt(v), name === 'pf' ? 'B2C' : 'B2B']} />
          <Bar dataKey="pf" stackId="a" fill={COLOR_PF} />
          <Bar dataKey="pj" stackId="a" fill={COLOR_PJ} radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <VerDados dados={data as unknown as Record<string, unknown>[]} />
    </div>
  )
}

// ── maiores operadoras ───────────────────────────────────────────────────────

function MaioresOperadorasMovel({ acessos }: { acessos: SiciMovelStats }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Maiores operadoras móveis</h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
            <th className="px-4 py-1.5 w-8 text-right">#</th>
            <th className="px-4 py-1.5">Operadora</th>
            <th className="px-4 py-1.5 w-28 text-right">Acessos</th>
            <th className="px-4 py-1.5 w-24 text-right">B2B</th>
            <th className="px-4 py-1.5 w-24 text-right">Munic.</th>
            <th className="px-4 py-1.5 w-20">Geração</th>
            <th className="px-4 py-1.5 w-36">ASN</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {acessos.top_operadoras.map((o, i) => (
            <tr key={o.cnpj} className="hover:bg-gray-50">
              <td className="px-4 py-1 text-right text-gray-400 tabular-nums">{i + 1}</td>
              <td className="px-4 py-1">
                <Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">
                  {o.empresa || o.razao_social}
                </Link>
              </td>
              <td className="px-4 py-1 text-right tabular-nums">{fmt(o.acessos)}</td>
              <td className="px-4 py-1 text-right tabular-nums text-gray-500">{fmt(o.acessos_pj)}</td>
              <td className="px-4 py-1 text-right tabular-nums text-gray-500">{fmt(o.municipios)}</td>
              <td className="px-4 py-1 text-gray-500">{o.geracao_predominante || '—'}</td>
              <td className="px-4 py-1">
                {o.asns.length ? (
                  <div className="flex flex-wrap gap-1">
                    {o.asns.slice(0, 2).map(a => (
                      <Link key={a} to={`/asn/${a}`}
                            className="text-xs px-1.5 py-0.5 rounded bg-primario-50 text-primario-700 border border-primario-100">
                        AS{a}
                      </Link>
                    ))}
                    {o.asns.length > 2 && <span className="text-xs text-gray-400">+{o.asns.length - 2}</span>}
                  </div>
                ) : <span className="text-xs text-gray-300">sem ASN</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── componente principal ─────────────────────────────────────────────────────────

export function BandaLargaMovelSection({ date }: { date?: string }) {
  const { data: smp, isError: smpError } = useQuery({
    queryKey: ['smp-stats', date],
    queryFn: () => fetchOutorgasStats('SMP', date),
    staleTime: 10 * 60 * 1000,
  })
  const { data: acessos } = useQuery({
    queryKey: ['acessos-movel-stats', date],
    queryFn: () => fetchAcessosMovelStats(date, 15),
    retry: false,
    staleTime: 10 * 60 * 1000,
  })

  if (smpError && !acessos) return null

  const licensed = smp?.unique_cnpjs ?? 0
  const withAsn = smp?.cnpjs_with_asn ?? 0
  const withoutAsn = Math.max(licensed - withAsn, 0)
  const pctComAsn = licensed > 0 ? (withAsn / licensed) * 100 : null
  const cobertura = acessos?.cobertura_declaracao

  const donut = [
    { name: 'Com ASN no mesmo CNPJ', value: withAsn, color: COLOR_WITH_ASN },
    { name: 'Sem ASN no mesmo CNPJ', value: withoutAsn, color: COLOR_WITHOUT_ASN },
  ]

  // a série nacional só traz o total por mês: sem divisão PF/PJ (soTotal), nada de área "B2C" igual ao total nem "B2B 0" (PANORAMA-E2)
  const serie: SiciSeriePoint[] = acessos
    ? acessos.serie_total.map(p => [p.mes, p.acessos, 0, 0])
    : []
  const b2cPct = acessos?.total_acessos ? (100 * acessos.acessos_pf) / acessos.total_acessos : 0

  return (
    <section className="space-y-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest border-t border-gray-100 pt-8"
          style={{ color: SECTION_COLOR }}>
        Telefonia móvel: SMP e SICI (Anatel)
        {acessos?.mes_referencia && (
          <span className="text-xs font-normal normal-case tracking-normal text-gray-400 ml-2">
            mês de referência {acessos.mes_referencia}
          </span>
        )}
      </h2>

      {/* Licenciamento × ASN × declaração */}
      {smp && (
        <div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">Licença, ASN e declaração</h3>
          <p className="text-xs text-gray-500 mb-4">
            Operadores com outorga de SMP (Serviço Móvel Pessoal), cruzados por CNPJ com os ASNs
            do Registro.br e com a declaração mensal de acessos ao SICI. Universo pequeno: as
            grandes operadoras móveis e MVNOs/M2M. O cruzamento é por CNPJ: uma operadora sem ASN pode usar a rede de outra empresa do grupo ou de um fornecedor, e ter ASN não garante anúncio na tabela BGP.
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-3">
              <StatCard value={fmt(licensed)} label="Operadores licenciados" sub={smp.rede_virtual ? `CNPJs com outorga SMP ou credenciamento de rede virtual (${fmt(smp.rede_virtual.credenciadas_sem_outorga_propria)} credenciadas sem outorga própria)` : 'CNPJs com outorga SMP ou credenciamento de rede virtual'} accent={SECTION_COLOR} />
              <StatCard value={fmt(withAsn)} label="…com ASN" sub="ASN no Registro.br com o mesmo CNPJ" accent={COLOR_WITH_ASN} />
              <StatCard value={fmt(withoutAsn)} label="…sem ASN" sub="nenhum ASN no Registro.br com o mesmo CNPJ" accent={COLOR_WITHOUT_ASN} />
              <StatCard value={fmtPct(pctComAsn)} label="Parcela com ASN" sub="licenciados com ASN no mesmo CNPJ" />
              {/* sem a razão sobre os licenciados (PANORAMA-E5): o cadastro inclui credenciadas de rede virtual, que não declaram por conta própria */}
              <StatCard value={fmt(cobertura?.informaram_sici)} label="…informaram no SICI"
                         sub={`declararam acessos móveis${acessos?.mes_referencia ? ` em ${acessos.mes_referencia}` : ''}; acessos de credenciada de rede virtual vêm na declaração da prestadora de origem (RGST, Res. Anatel 777/2025)`} />
              <StatCard value={fmt(acessos?.acessos_m2m)} label="Acessos M2M" sub="chips máquina-a-máquina, fora do total" />
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col">
              <div className="text-xs text-gray-500 mb-1">Operadores licenciados</div>
              <div className="relative flex-1 flex items-center justify-center">
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={donut} dataKey="value" innerRadius={48} outerRadius={68} paddingAngle={2} startAngle={90} endAngle={-270}>
                      {donut.map(e => <Cell key={e.name} fill={e.color} aria-label={e.name} />)}
                    </Pie>
                    <Tooltip formatter={(v: number, name: string) => [fmt(v), name]} />
                  </PieChart>
                </ResponsiveContainer>
                <VerDados dados={donut as unknown as Record<string, unknown>[]} />
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <div className="text-lg font-bold tabular-nums text-gray-800">{fmtPct(pctComAsn, 0)}</div>
                  <div className="text-xs text-gray-400">com ASN</div>
                </div>
              </div>
              <div className="flex justify-center gap-3 text-xs text-gray-600">
                {donut.map(e => (
                  <span key={e.name} className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: e.color }} />
                    {e.name.split(' ')[0]}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rede virtual (MVNO credenciado x host) */}
      {smp && smp.rede_virtual && (smp.rede_virtual.hosts > 0 || smp.rede_virtual.credenciadas > 0) && (
        <div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">Rede virtual (MVNO)</h3>
          <p className="text-xs text-gray-500 mb-4">
            Operadoras que exploram o SMP por credenciamento a uma Prestadora Origem (host), em vez
            de outorga própria. O cruzamento usa o conjunto de dados da Anatel sobre Empresas
            Credenciadas de Rede Virtual.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <StatCard value={fmt(smp.rede_virtual.hosts)} label="Hosts" sub="prestadoras origem que credenciam terceiros" accent={SECTION_COLOR} />
            <StatCard value={fmt(smp.rede_virtual.credenciadas)} label="Credenciadas (MVNO)" sub="operando via contrato de rede virtual" accent={COLOR_WITH_ASN} />
            <StatCard value={fmt(smp.rede_virtual.credenciadas_sem_outorga_propria)} label="…sem outorga SMP própria"
                       sub="invisíveis no universo SMP até esta fase" accent={COLOR_WITHOUT_ASN} />
          </div>
        </div>
      )}

      {/* Acessos totais B2C/B2B */}
      {acessos && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard value={fmt(acessos.total_acessos)} label="Acessos móveis declarados" sub="exclui M2M e ponto de serviço" accent={SECTION_COLOR} />
          <StatCard value={fmt(acessos.acessos_pf)} label="B2C" sub={`${b2cPct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} accent={COLOR_PF} />
          <StatCard value={fmt(acessos.acessos_pj)} label="B2B" sub={`${(100 - b2cPct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} accent={COLOR_PJ} />
          <StatCard value={fmt(acessos.municipios_atendidos)} label="Municípios atendidos" />
        </div>
      )}

      {/* Geografia */}
      {smp && acessos && (
        <div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">Geografia: licenciamento × acessos</h3>
          <p className="text-xs text-gray-500 mb-4">
            Outorgas SMP (cadastro, sede da operadora) ao lado dos acessos móveis efetivamente
            declarados (uso, por macrorregião do assinante).
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <OutorgasPorUf smp={smp} />
            <AcessosPorRegiao acessos={acessos} />
          </div>
        </div>
      )}

      {/* Evolução nacional */}
      {acessos && serie.length > 1 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-1">
            Evolução nacional de acessos móveis
            <span className="font-normal text-gray-400">{' '}· {serie[0][0]} a {serie[serie.length - 1][0]}</span>
          </h3>
          <AccessHistoryChart serie={serie} meses={serie.length} soTotal />
        </div>
      )}

      {/* Geração / modalidade */}
      {acessos && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Geração de rede <span className="font-normal text-gray-500">(todas as linhas, inclusive M2M e ponto de serviço)</span></h3>
            <Barras dados={acessos.por_geracao} total={somaValores(acessos.por_geracao)} />
            <p className="mt-1 text-xs text-gray-500">Base: {fmt(somaValores(acessos.por_geracao))} linhas; o total de acessos acima ({fmt(acessos.total_acessos)}) conta só o produto padrão.</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Modalidade de cobrança <span className="font-normal text-gray-500">(todas as linhas, inclusive M2M e ponto de serviço)</span></h3>
            <Barras dados={acessos.por_modalidade} total={somaValores(acessos.por_modalidade)} />
            <p className="mt-1 text-xs text-gray-500">Base: {fmt(somaValores(acessos.por_modalidade))} linhas.</p>
          </div>
        </div>
      )}

      {/* Maiores operadoras */}
      {acessos && <MaioresOperadorasMovel acessos={acessos} />}
    </section>
  )
}
