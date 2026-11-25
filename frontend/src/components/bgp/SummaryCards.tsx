import { composicaoPorPrefixo, type RoutingAnalysis } from '../../types/routingAnalysis'
import { Tip } from './BgpShared'

interface Props { data: RoutingAnalysis }

function fmt(n: number) { return n.toLocaleString('pt-BR') }

type Accent = 'blue' | 'green' | 'orange' | 'purple' | 'amber' | 'gray'

const ACCENT: Record<Accent, { bg: string; border: string; value: string }> = {
  blue:   { bg: 'bg-primario-50',    border: 'border-primario-200',    value: 'text-primario-700' },
  green:  { bg: 'bg-mercado-50', border: 'border-mercado-200', value: 'text-mercado-700' },
  orange: { bg: 'bg-alerta-50',  border: 'border-alerta-200',  value: 'text-alerta-700' },
  purple: { bg: 'bg-v6-50',  border: 'border-v6-200',  value: 'text-v6-700' },
  amber:  { bg: 'bg-aviso-50',   border: 'border-aviso-200',   value: 'text-aviso-700' },
  gray:   { bg: 'bg-white',      border: 'border-gray-200',    value: 'text-gray-900' },
}

function Card({ label, value, sub, tooltip, accent = 'gray' }: {
  label: string; value: string; sub?: string; tooltip: string; accent?: Accent
}) {
  const { bg, border, value: valCls } = ACCENT[accent]
  return (
    <div className={`${bg} rounded-lg border ${border} p-4`}>
      <div className="text-xs text-gray-500 mb-1 flex items-start gap-0.5">
        <span>{label}</span>
        <Tip text={tooltip} />
      </div>
      <div className={`text-2xl font-semibold ${valCls}`}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export function SummaryCards({ data }: Props) {
  const porPrefixo = composicaoPorPrefixo(data)
  const v4 = data.summary.v4
  const v6 = data.summary.v6
  const ms_v4 = data.more_specifics.v4
  const ms_v6 = data.more_specifics.v6
  const ts_v4 = data.too_specific.v4.length
  const ts_v6 = data.too_specific.v6.length

  const pct4 = ms_v4.pbr_root + ms_v4.pbr_more_specific > 0
    ? ((ms_v4.pbr_more_specific / (ms_v4.pbr_root + ms_v4.pbr_more_specific)) * 100).toFixed(1)
    : '0.0'

  const pct6 = ms_v6.pbr_root + ms_v6.pbr_more_specific > 0
    ? ((ms_v6.pbr_more_specific / (ms_v6.pbr_root + ms_v6.pbr_more_specific)) * 100).toFixed(1)
    : '0.0'

  return (
    <div className="space-y-2">
      {/* Linha IPv6 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card
          accent="blue"
          label="Rotas BR (IPv6)"
          value={fmt(v6.pbr_routes)}
          sub={`${v6.pbr_pct.toFixed(2)}% da tabela global`}
          tooltip={porPrefixo ? "Rotas IPv6 na tabela de roteamento global com prefixo contido em bloco alocado pelo Registro.br; a origem do anúncio não define." : "Rotas IPv6 na tabela global com prefixo alocado pelo Registro.br ou origem num ASN da lista do Registro.br (regra anterior à atual, como este snapshot foi gerado)."}
        />
        <Card
          accent="blue"
          label="ASNs BR com IPv6"
          value={fmt(v6.br_origin_asns)}
          sub="ASNs com pelo menos 1 rota IPv6"
          tooltip="Sistemas autônomos brasileiros que aparecem como originadores de pelo menos uma rota IPv6 na tabela global."
        />
        <Card
          accent="amber"
          label="More specifics (IPv6)"
          value={`${pct6}%`}
          sub={`${fmt(ms_v6.pbr_more_specific)} de ${fmt(ms_v6.pbr_root + ms_v6.pbr_more_specific)} rotas`}
          tooltip="Proporção das rotas brasileiras IPv6 que são mais específicas (sub-blocos) de outro prefixo já anunciado. Pode indicar engenharia de tráfego legítima ou fragmentação desnecessária da tabela."
        />
        <Card
          accent="orange"
          label="Filtráveis IPv6 (>/48)"
          value={fmt(ts_v6)}
          sub="prefixos abaixo do limite"
          tooltip="Prefixos IPv6 mais específicos que /48. Podem ser filtrados por operadores de backbone, pois excedem o limite de granularidade convencionalmente aceito na Internet pública."
        />
        <Card
          accent="gray"
          label="Prefixos globais IPv6"
          value={fmt(v6.total_prefixes_global)}
          sub={`${fmt(v6.total_asns_global)} ASNs originadores`}
          tooltip="Total de prefixos IPv6 na tabela de roteamento global no momento da coleta, conforme vistos pelos coletores RouteViews e/ou RIPE RIS."
        />
      </div>

      {/* Linha IPv4 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card
          accent="green"
          label="Rotas BR (IPv4)"
          value={fmt(v4.pbr_routes)}
          sub={`${v4.pbr_pct.toFixed(2)}% da tabela global`}
          tooltip={porPrefixo ? "Rotas IPv4 na tabela de roteamento global com prefixo contido em bloco alocado pelo Registro.br; a origem do anúncio não define." : "Rotas IPv4 na tabela global com prefixo alocado pelo Registro.br ou origem num ASN da lista do Registro.br (regra anterior à atual, como este snapshot foi gerado)."}
        />
        <Card
          accent="green"
          label="ASNs BR com IPv4"
          value={fmt(v4.br_origin_asns)}
          sub="ASNs com pelo menos 1 rota IPv4"
          tooltip="Sistemas autônomos brasileiros que aparecem como originadores de pelo menos uma rota IPv4 na tabela global."
        />
        <Card
          accent="amber"
          label="More specifics (IPv4)"
          value={`${pct4}%`}
          sub={`${fmt(ms_v4.pbr_more_specific)} de ${fmt(ms_v4.pbr_root + ms_v4.pbr_more_specific)} rotas`}
          tooltip="Proporção das rotas brasileiras IPv4 que são mais específicas (sub-blocos) de outro prefixo já anunciado. Pode indicar engenharia de tráfego legítima ou fragmentação desnecessária da tabela."
        />
        <Card
          accent="orange"
          label="Filtráveis IPv4 (>/24)"
          value={fmt(ts_v4)}
          sub="prefixos abaixo do limite"
          tooltip="Prefixos IPv4 mais específicos que /24. Podem ser filtrados por operadores de backbone, pois excedem o limite de granularidade convencionalmente aceito na Internet pública."
        />
        <Card
          accent="gray"
          label="Prefixos globais IPv4"
          value={fmt(v4.total_prefixes_global)}
          sub={`${fmt(v4.total_asns_global)} ASNs originadores`}
          tooltip="Total de prefixos IPv4 na tabela de roteamento global no momento da coleta, conforme vistos pelos coletores RouteViews e/ou RIPE RIS."
        />
      </div>

      {/* Linha global */}
      <div className="grid grid-cols-2 gap-3">
        <Card
          accent="gray"
          label="ASNs BR visíveis na tabela"
          value={`${fmt(data.br_asns_visible ?? 0)} / ${fmt(data.br_asns_registered ?? 0)}`}
          sub={porPrefixo ? 'visíveis dos ASNs brasileiros (delegação LACNIC)' : 'visíveis de alocados pelo Registro.br'}
          tooltip={porPrefixo
            ? 'Sistemas autônomos brasileiros (delegados pela LACNIC ao Brasil) que aparecem como originadores de pelo menos uma rota (IPv6 ou IPv4) na tabela global, sobre o total deles. Diferença indica ASNs sem anúncios visíveis nos coletores utilizados.'
            : 'Sistemas autônomos da lista do Registro.br (inclui empresas estrangeiras com CNPJ no Brasil) que aparecem como originadores de pelo menos uma rota na tabela global, sobre o total da lista, como este snapshot foi gerado.'}
        />
      </div>
    </div>
  )
}
