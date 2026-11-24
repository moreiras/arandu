// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { Kpi } from '../../components/ui'
import { EstadoDados } from '../../components/ui/EstadoDados'
import { fetchCDNPresence, fetchIXPs } from '../../services/api'
import { CoberturaIxbr } from './CoberturaIxbr'
import { useResumo } from './useResumo'
import { fracao, grande, num, pct } from './formato'

const LINKS: Array<[string, string]> = [['/ixps', 'PTTs'], ['/cdns', 'CDNs e conteúdo'], ['/instalacoes', 'Datacenters'], ['/communities', 'Route servers e communities']]

/**
 * Aba Interconexão do Panorama técnico: PTTs, participantes, alcance e CDNs no agregado,
 * e os gráficos de ASNs por PTT. A cobertura de endereços por PTT fica nas abas IPv6 e IPv4; a tabela global × IX.br fica em /ixps.
 */
export function AbaInterconexao() {
  const { date, summary: s } = useResumo()
  const ixps = useQuery({ queryKey: ['ixps', date], queryFn: () => fetchIXPs(date ?? undefined), staleTime: Infinity, gcTime: Infinity })
  const cdns = useQuery({ queryKey: ['cdn-presence', date], queryFn: () => fetchCDNPresence(date ?? undefined), staleTime: Infinity, gcTime: Infinity, retry: false })
  const ix = s?.ixp_aggregate
  const gt = s?.global_table
  const ref = s?.snapshot_date ?? date
  const c = cdns.data
  const cdnsNoIxbr = c ? c.cdns.filter((x) => x.ixbr_count > 0).length : null
  const pttsComCdn = c ? c.ixbr_columns.filter((x) => x.cdn_count > 0).length : null
  const topPtts = c ? [...c.ixbr_columns].sort((a, b) => b.cdn_count - a.cdn_count).slice(0, 5) : []
  return (
    <div className="space-y-10" data-testid="aba-interconexao">
      <p className="flex flex-wrap gap-x-4 text-sm">{LINKS.map(([to, r]) => <Link key={to} to={to} className="text-primario-700 hover:underline">{r} →</Link>)}</p>

      <section className="space-y-3" aria-label="PTTs e participantes">
        <h2 className="text-titulo-3 text-gray-800">PTTs e participantes</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Kpi rotulo="PTTs do IX.br" valor={num(ixps.data?.ixps.length)} tom="primario" referencia={s?.ixps_missing ? `${num(s.ixps_missing)} sem dados neste snapshot` : undefined} fonte="looking glasses do IX.br" dataRef={ref} />
          <Kpi rotulo="Participantes diretos" valor={num(ix?.asn_direct_union_count)} explicacao="ASNs com sessão BGP no route server de algum PTT do IX.br (brasileiros ou não), sem repetição entre PTTs." fonte="looking glasses do IX.br" dataRef={ref} />
          <Kpi rotulo="ASNs com rotas vistas no IX.br" valor={num(ix?.asn_origin_union_count)} explicacao="ASNs (de qualquer país) que originam prefixos vistos em algum PTT do IX.br, diretamente ou por trânsito." fonte="looking glasses do IX.br" dataRef={ref} />
          <Kpi rotulo="ASNs BR com rotas vistas no IX.br" valor={num(ix?.br_asns_origin_union_count)} referencia={pct(fracao(ix?.br_asns_origin_union_count, gt?.br_asns_in_ft)) ? `${pct(fracao(ix?.br_asns_origin_union_count, gt?.br_asns_in_ft))} dos visíveis na tabela global` : undefined}
            explicacao="ASNs do Registro.br que originam prefixos vistos em algum PTT do IX.br, inclusive por trânsito: não é participação direta." fonte="looking glasses do IX.br" dataRef={ref} />
          <Kpi rotulo="ASNs BR em PTTs fora do IX.br" valor={num(s?.external_ixps_br_asn_union_count)} explicacao="ASNs do Registro.br inscritos no PeeringDB em algum PTT que não é do IX.br, sem repetição." fonte="PeeringDB" dataRef={ref} />
          <Kpi rotulo="Usuários alcançáveis via IX.br (IPv4, estimativa)" valor={grande(s?.ixp_estimated_users_v4)} tom="estimado"
            explicacao="Usuários estimados do APNIC atrás do espaço IPv4 visto na união dos PTTs do IX.br." fonte="APNIC Labs e looking glasses do IX.br" dataRef={ref} />
        </div>
      </section>

      <section className="space-y-3" aria-label="CDNs e conteúdo">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4">
          <h2 className="text-titulo-3 text-gray-800">CDNs e conteúdo</h2>
          <Link to="/cdns" className="text-sm text-primario-700 hover:underline">Presença por PTT →</Link>
        </div>
        {cdns.isError ? <EstadoDados erro={cdns.error} oQue="a presença de CDNs" mensagem="A presença de CDNs não está disponível neste snapshot." /> : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Kpi rotulo="CDNs e CAPs em PTTs do IX.br" valor={cdnsNoIxbr == null ? null : `${num(cdnsNoIxbr)} de ${num(c?.cdns.length)}`}
                explicacao="Provedores de CDN e de conteúdo acompanhados pelo site que participam de ao menos um PTT do IX.br." fonte="IX.br e PeeringDB" dataRef={c?.snapshot_date} />
              <Kpi rotulo="PTTs do IX.br com alguma CDN" valor={pttsComCdn == null ? null : `${num(pttsComCdn)} de ${num(c?.ixbr_columns.length)}`} fonte="IX.br" dataRef={c?.snapshot_date} />
            </div>
            {topPtts.length > 0 && (
              <p className="text-sm text-gray-700">PTTs com mais CDNs e CAPs: {topPtts.map((p, i) => <span key={p.code}>{i > 0 && ', '}<Link to={`/ixp/${p.code}`} className="text-primario-700 hover:underline">{p.name}</Link> ({num(p.cdn_count)})</span>)}.</p>
            )}
          </>
        )}
      </section>

      <section className="space-y-3" aria-label="ASNs por PTT">
        <h2 className="text-titulo-3 text-gray-800">ASNs por PTT</h2>
        <CoberturaIxbr grupos={['asns']} />
      </section>

      <p className="text-sm text-gray-600">A comparação entre a tabela global e a união dos PTTs, por ASNs e por família, está em <Link to="/ixps" className="text-primario-700 hover:underline">PTTs</Link>, junto da lista dos PTTs.</p>
    </div>
  )
}
