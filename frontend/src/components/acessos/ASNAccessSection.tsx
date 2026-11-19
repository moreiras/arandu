import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchASNAcessos, fetchASNAcessosMunicipios } from '../../services/api'
import { AccessMunicipioMap } from './AccessMunicipioMap'
import { AccessHistoryChart } from './AccessHistoryChart'
import type { SiciDivergencia } from '../../types/api'

const fmt = (n: number | undefined | null) =>
  n == null ? '—' : n.toLocaleString('pt-BR')

function fmtCapacidade(mbps: number | undefined): string {
  if (!mbps) return '—'
  if (mbps >= 1e6) return `${(mbps / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Tbps`
  if (mbps >= 1e3) return `${(mbps / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Gbps`
  return `${mbps.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} Mbps`
}

function KPI({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="px-3 py-2 rounded-lg bg-gray-50 border border-gray-100">
      <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold text-gray-900 tabular-nums leading-tight">{value}</div>
      {hint && <div className="text-xs text-gray-400">{hint}</div>}
    </div>
  )
}

/**
 * Leitura da divergência entre as duas fontes.
 *
 * O APNIC observa usuários e atribui a ASN; a operadora declara contratos por CNPJ.
 * A divergência é hipótese a investigar, não erro de uma das fontes — o texto oferece
 * as leituras possíveis e não crava veredito.
 */
function DivergenciaBox({ div, apnicUsers }: {
  div: SiciDivergencia | null | undefined
  apnicUsers?: number | null
}) {
  if (!div) return null
  if (div.classificacao === 'nao_comparavel') {
    return (
      <div className="text-xs text-gray-500 bg-aviso-50 border border-aviso-100 rounded-lg px-3 py-2">
        Comparação com o APNIC não se aplica: o CNPJ desta operadora tem mais de um AS,
        e os acessos declarados valem para o CNPJ inteiro.
      </div>
    )
  }
  if (div.classificacao === 'sem_dados' || div.razao == null) return null

  const alto = div.classificacao === 'apnic_alto'
  const baixo = div.classificacao === 'apnic_baixo'
  const tone = alto ? 'bg-alerta-50 border-alerta-100'
    : baixo ? 'bg-v6-50 border-v6-100'
    : 'bg-mercado-50 border-mercado-100'

  return (
    <div className={`text-xs rounded-lg px-3 py-2 border ${tone}`}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-gray-500">Usuários estimados (APNIC)</span>
        <strong className="tabular-nums text-gray-900">{fmt(div.apnic_users ?? apnicUsers)}</strong>
        <span className="text-gray-400">÷</span>
        <span className="text-gray-500">acessos declarados (Anatel)</span>
        <strong className="tabular-nums text-gray-900">{fmt(div.acessos_sici)}</strong>
        <span className="text-gray-400">=</span>
        <strong className="tabular-nums text-gray-900">{div.razao.toLocaleString('pt-BR')}</strong>
        <span className="text-gray-400">usuários por contrato</span>
      </div>
      <div className="text-gray-500 mt-1 leading-relaxed">
        {!alto && !baixo && (
          <>Dentro da faixa esperada (mediana nacional de 3,97 usuários por contrato).</>
        )}
        {alto && (
          <>Bem acima do esperado. Leituras possíveis: CGNAT concentrando muitos usuários
             por acesso, tráfego de terceiros (trânsito ou atacado) cursando este AS, ou
             atribuição de ASN imprecisa no APNIC. As duas fontes medem coisas
             diferentes — a divergência é ponto de partida, não veredito.</>
        )}
        {baixo && (
          <>Abaixo de 1 usuário por contrato. Leituras possíveis: os acessos do CNPJ
             saem por outros ASes, o tráfego cursa um AS de trânsito, ou são links
             corporativos que não geram usuários observáveis pelo APNIC.</>
        )}
      </div>
    </div>
  )
}

export function ASNAccessSection({ asn, date, apnicUsers }: {
  asn: number
  date?: string
  apnicUsers?: number | null
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['asn-acessos', asn, date],
    queryFn: () => fetchASNAcessos(asn, date),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  const { data: muns } = useQuery({
    queryKey: ['asn-acessos-mun', asn, date],
    queryFn: () => fetchASNAcessosMunicipios(asn, date),
    enabled: !!data,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  // Sem dados do SICI a seção simplesmente não aparece — nem todo AS é operadora
  // licenciada, e a maioria dos ASes BR não declara acessos.
  if (isLoading || !data) return null

  const b2cPct = data.acessos ? (100 * data.pf) / data.acessos : 0
  const items = muns?.items ?? []

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h2 className="text-base font-semibold text-gray-800 mb-1 flex items-center gap-2">
        Base de assinantes declarada à Anatel
        <span className="text-xs font-normal text-gray-400">
          SICI · mês de referência {data.mes_referencia}
        </span>
      </h2>
      <div className="text-xs text-gray-500 mb-3">
        Declaração mensal obrigatória da operadora{' '}
        <Link to={`/operadora/${data.cnpj}`} className="text-primario-600 hover:underline">
          {data.empresa || data.cnpj}
        </Link>
        {data.acessos_compartilhados && (
          <span className="ml-1 text-aviso-700">
            — este CNPJ tem {data.asns.length} ASes, e o total declarado vale para o CNPJ
            inteiro (não some os ASes entre si).
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 mb-4">
        <KPI label="Acessos" value={fmt(data.acessos)} />
        <KPI label="B2C" value={fmt(data.pf)}
             hint={`${b2cPct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% do total`} />
        <KPI label="B2B" value={fmt(data.pj)}
             hint={`${(100 - b2cPct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} />
        <KPI label="Municípios" value={fmt(data.municipios)} />
        <KPI label="Capacidade contratada" value={fmtCapacidade(data.capacidade_mbps)}
             hint="soma de velocidade × acessos" />
        <KPI label="Velocidade mediana"
             value={`${fmt(Math.round(data.velocidade_mediana_mbps))} Mbps`}
             hint={`média ${fmt(Math.round(data.velocidade_media_mbps))}`} />
      </div>

      <div className="mb-4">
        <DivergenciaBox div={data.divergencia_apnic_anatel} apnicUsers={apnicUsers} />
      </div>

      {items.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-700 mb-1.5">
            Distribuição pelos municípios atendidos
          </h3>
          <AccessMunicipioMap municipios={items} />
        </div>
      )}

      {data.serie?.length > 1 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-700 mb-1.5">
            Evolução mensal
            <span className="font-normal text-gray-400">
              {' '}· {data.serie[0][0]} a {data.serie[data.serie.length - 1][0]}
            </span>
          </h3>
          <AccessHistoryChart serie={data.serie} meses={data.serie.length} />
        </div>
      )}

      {items.length > 0 && (
        <details>
          <summary className="text-sm font-medium text-gray-700 cursor-pointer">
            Municípios atendidos ({items.length})
          </summary>
          <div className="mt-2 max-h-80 overflow-y-auto border border-gray-100 rounded-lg">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                  <th className="px-3 py-1.5">Município</th>
                  <th className="px-3 py-1.5 w-14">UF</th>
                  <th className="px-3 py-1.5 w-24 text-right">Acessos</th>
                  <th className="px-3 py-1.5 w-20 text-right">B2B</th>
                  <th className="px-3 py-1.5 w-24 text-right">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {items.slice(0, 300).map(m => (
                  <tr key={m.ibge} className="hover:bg-gray-50">
                    <td className="px-3 py-1">
                      <Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">
                        {m.nome}
                      </Link>
                    </td>
                    <td className="px-3 py-1 text-gray-500">{m.uf}</td>
                    <td className="px-3 py-1 text-right tabular-nums">{fmt(m.acessos)}</td>
                    <td className="px-3 py-1 text-right tabular-nums text-gray-500">{fmt(m.pj)}</td>
                    <td className="px-3 py-1 text-right tabular-nums text-gray-500">
                      {m.share == null ? '—' : `${m.share.toLocaleString('pt-BR')}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <div className="text-xs text-gray-400 mt-3 leading-relaxed">
        Fonte: declaração mensal ao SICI (Anatel), mês de referência {data.mes_referencia} —
        data distinta da do snapshot. Capacidade é a contratada pelos assinantes
        (soma de velocidade × acessos), não capacidade de trânsito ou de backhaul.
      </div>
    </div>
  )
}
