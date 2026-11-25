// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { Kpi, NotaVariosTotais } from '../../components/ui'
import { SinteseTopo } from '../../components/ui/SinteseTopo'
import { REGRAS_SINTESE_TECNICA, sinteseTecnica } from './sinteseTecnica'
import { rotuloDe } from '../../lib/universos'
import { HomeMap } from '../../components/maps/HomeMap'
import { SnapshotHealth } from '../dashboard/Estatisticas'
import { fetchCDNPresence, fetchDiffSnapshots, fetchIXPs } from '../../services/api'
import { useSnapshots } from '../../hooks/useSnapshot'
import { ComoLerNumerosPais, EXPLICA, referenciaMedicao, useBrasilIndicadores } from './IndicadoresBrasil'
import { useResumo } from './useResumo'
import { fracao, grande, num, pct } from './formato'

/** Um tema do resumo: título, uma linha de KPIs e os links para onde o tema é detalhado. */
function Tema({ titulo, links, children }: { titulo: string; links: Array<[string, string]>; children: ReactNode }) {
  return (
    <section className="space-y-2" aria-label={titulo}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 className="text-titulo-3 text-gray-800">{titulo}</h2>
        <p className="flex flex-wrap gap-x-3 text-sm">
          {links.map(([to, rotulo]) => <Link key={to} to={to} className="text-primario-700 hover:underline">{rotulo} →</Link>)}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{children}</div>
    </section>
  )
}

/**
 * Aba Resumo do Panorama técnico: um número por conceito, agrupado por tema, cada tema levando à aba ou página que o detalha.
 * Substitui os quatro blocos herdados da Visão geral e de Estatísticas, que repetiam os mesmos totais e traziam dados de mercado. O mapa fica no fim, ilustrativo.
 */
export function ResumoTecnico() {
  const { date, summary: s, carregando } = useResumo()
  const { data: br } = useBrasilIndicadores()
  const ixps = useQuery({ queryKey: ['ixps', date], queryFn: () => fetchIXPs(date ?? undefined), staleTime: Infinity, gcTime: Infinity })
  const cdns = useQuery({ queryKey: ['cdn-presence', date], queryFn: () => fetchCDNPresence(date ?? undefined), staleTime: Infinity, gcTime: Infinity, retry: false })
  // Variação do percentual de usuários com IPv6 desde o snapshot anterior, calculada pela API na mesma base (regra de comparabilidade, PT-28)
  const snaps = (useSnapshots().data?.snapshots ?? [])
  const anterior = snaps.length >= 2 && date === snaps[snaps.length - 1] ? snaps[snaps.length - 2] : null
  const diff = useQuery({ queryKey: ['diff', anterior, date], queryFn: () => fetchDiffSnapshots(anterior as string, date as string), enabled: !!anterior && !!date, staleTime: Infinity, gcTime: Infinity, retry: false })
  const razao = diff.data?.razoes?.ipv6_pct_usuarios
  const variacaoV6 = razao?.comparavel && razao.variacao_pp != null
    ? { texto: `${razao.variacao_pp >= 0 ? '+' : ''}${razao.variacao_pp.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} p.p. desde ${anterior} (série semanal)` }
    : undefined
  const gt = s?.global_table
  const ix = s?.ixp_aggregate
  const ref = s?.snapshot_date ?? date
  const pub = br?.rpki?.publicacao
  const rotas = br?.rpki?.rotas?.rpki
  const cdnsNoIxbr = cdns.data ? cdns.data.cdns.filter((c) => c.ixbr_count > 0).length : null
  const pttsIxbr = s ? (s.ixps_ok ?? 0) + (s.ixps_partial ?? 0) + (s.ixps_missing ?? 0) : null
  return (
    <div className="space-y-8" data-testid="resumo-tecnico">
      <SinteseTopo frases={sinteseTecnica(s, br, ref)} snapshot={ref} regras={REGRAS_SINTESE_TECNICA} />
      <SnapshotHealth summary={s} loading={carregando} />
      <NotaVariosTotais />

      <Tema titulo="Recursos e visibilidade" links={[['?aba=ipv6', 'IPv6'], ['?aba=ipv4', 'IPv4'], ['/bgp', 'Tabela BGP']]}>
        <Kpi selo="fato" rotulo={rotuloDe('asnsLacnic')} valor={num(s?.total_asns_br)} tom="primario" fonte="LACNIC (delegated-extended)" dataRef={ref} />
        <Kpi selo="fato" rotulo={rotuloDe('asnsVisiveis')} valor={num(gt?.br_asns_in_ft)} referencia={pct(fracao(gt?.br_asns_in_ft, s?.total_asns_br)) ? `${pct(fracao(gt?.br_asns_in_ft, s?.total_asns_br))} dos ASNs brasileiros (LACNIC)` : undefined}
          explicacao="ASNs brasileiros (delegados pela LACNIC ao Brasil) que originam ao menos um prefixo na tabela de roteamento global (RouteViews)." fonte="RouteViews e LACNIC" dataRef={ref} />
        <Kpi selo="fato" rotulo="Espaço IPv6 alocado visível na tabela global" valor={pct(gt?.v6_br_coverage_pct)} tom="v6" explicacao="Parte do espaço IPv6 alocado pelo Registro.br que aparece anunciado na tabela global." fonte="RouteViews e Registro.br" dataRef={ref} />
        <Kpi selo="fato" rotulo="Espaço IPv4 alocado visível na tabela global" valor={pct(gt?.v4_br_coverage_pct)} tom="v4" explicacao="Parte do espaço IPv4 alocado pelo Registro.br que aparece anunciado na tabela global." fonte="RouteViews e Registro.br" dataRef={ref} />
      </Tema>

      <Tema titulo="Usuários e IPv6" links={[['?aba=ipv6', 'IPv6'], ['/uso-da-internet', 'Uso da Internet (Cetic.br)']]}>
        <Kpi selo="estimado" rotulo="Usuários estimados" valor={grande(br?.ipv6.usuarios)} tom="estimado" explicacao="Soma das estimativas de usuários do APNIC Labs por ASN do Brasil. É outra medida que a da TIC Domicílios (pesquisa domiciliar do Cetic.br), em Uso da Internet." fonte="APNIC Labs" dataRef={br?.snapshot_date} />
        <Kpi selo="estimado" rotulo="Usuários com IPv6 (estimativa)" valor={pct(br?.ipv6.pct_usuarios_ipv6)} tom="v6" variacao={variacaoV6} explicacao={EXPLICA.ipv6} fonte="APNIC Labs" dataRef={br?.snapshot_date} />
        <Kpi selo="fato" rotulo={rotuloDe('asnsAnunciamV6')} valor={pct(fracao(s?.br_asns_ft_v6, gt?.br_asns_in_ft))} tom="v6" referencia={s?.br_asns_ft_v6 != null && gt?.br_asns_in_ft ? `${num(s.br_asns_ft_v6)} dos ${num(gt.br_asns_in_ft)} visíveis` : undefined}
          explicacao="ASNs do Brasil com ao menos um prefixo IPv6 na tabela global, entre os que aparecem nela. Ter IPv6 alocado sem anunciar não conta." fonte="RouteViews e LACNIC" dataRef={ref} />
      </Tema>

      <Tema titulo="Interconexão e conteúdo" links={[['?aba=interconexao', 'Interconexão'], ['/ixps', 'PTTs'], ['/cdns', 'CDNs']]}>
        <Kpi selo="fato" rotulo="PTTs do IX.br" valor={num(pttsIxbr ?? ixps.data?.ixps.length)} tom="primario" referencia={s?.ixps_missing ? `${num(s.ixps_missing)} sem dados neste snapshot` : undefined} fonte="looking glasses do IX.br" dataRef={ref} />
        <Kpi selo="fato" rotulo={rotuloDe('sessaoRs')} valor={num(ix?.asn_direct_union_count)} explicacao="ASNs com sessão BGP no route server de algum PTT do IX.br (brasileiros ou não), sem repetição entre PTTs." fonte="looking glasses do IX.br" dataRef={ref} />
        <Kpi selo="fato" rotulo={rotuloDe('originadoresBr')} valor={num(ix?.br_asns_origin_union_count)} referencia={pct(fracao(ix?.br_asns_origin_union_count, gt?.br_asns_in_ft)) ? `${pct(fracao(ix?.br_asns_origin_union_count, gt?.br_asns_in_ft))} dos ASNs brasileiros visíveis na tabela global` : undefined}
          explicacao="ASNs brasileiros que originam prefixos vistos em algum PTT do IX.br, inclusive os que chegam por um provedor de trânsito: não é participação direta." fonte="looking glasses do IX.br" dataRef={ref} />
        <Kpi selo="inferido" rotulo="CDNs e CAPs em PTTs do IX.br" valor={cdnsNoIxbr == null ? null : `${num(cdnsNoIxbr)} de ${num(cdns.data?.cdns.length)}`} explicacao="Provedores de CDN e de conteúdo acompanhados pelo site que são participantes de ao menos um PTT do IX.br." fonte="IX.br e PeeringDB" dataRef={cdns.data?.snapshot_date} />
      </Tema>

      <Tema titulo="Segurança" links={[['?aba=seguranca', 'Segurança'], ['/seguranca-de-roteamento', 'Por UF e porte']]}>
        <Kpi selo="fato" rotulo="ASNs com ROA" valor={pct(fracao(pub?.br_asns_with_roa, pub?.br_asns_total))} tom="tecnico" referencia={pub ? `${num(pub.br_asns_with_roa)} de ${num(pub.br_asns_total)}` : undefined}
          explicacao="ASNs do Registro.br que publicaram ao menos uma ROA no RPKI." fonte="RPKI (Routinator)" dataRef={br?.snapshot_date} />
        <Kpi selo="fato" rotulo="Rotas BR RPKI-válidas (IPv6 · IPv4)" valor={rotas ? `${pct(rotas.v6.pct.valid) ?? '—'} · ${pct(rotas.v4.pct.valid) ?? '—'}` : null} tom="tecnico"
          explicacao="Rotas brasileiras na tabela global cuja origem é confirmada por uma ROA (RFC 6811). O restante é inválido ou sem ROA; o detalhe está na aba Segurança." fonte="RouteViews e RPKI" dataRef={br?.rpki?.rotas?.snapshot_date} />
        <Kpi selo="estimado" rotulo="Filtragem de rotas inválidas (ROV, média ponderada por amostras)" valor={pct(br?.rov?.media_ponderada_pct, 2)} tom="tecnico" referencia={referenciaMedicao(br?.rov)} explicacao={EXPLICA.rov} fonte="APNIC Labs" dataRef={br?.rov?.fonte?.as_of ?? br?.snapshot_date} />
        <Kpi selo="estimado" rotulo="Validação de DNSSEC (média ponderada por amostras)" valor={pct(br?.dnssec?.media_ponderada_pct, 2)} tom="tecnico" referencia={referenciaMedicao(br?.dnssec)} explicacao={EXPLICA.dnssec} fonte="APNIC Labs" dataRef={br?.dnssec?.fonte?.as_of ?? br?.snapshot_date} />
      </Tema>

      <ComoLerNumerosPais />

      <section className="space-y-2" aria-label="Mapa ilustrativo">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4">
          <h2 className="text-titulo-3 text-gray-800">No mapa</h2>
          <Link to="/mapa" className="text-sm text-primario-700 hover:underline">Explorar no Mapa →</Link>
        </div>
        <p className="text-sm text-gray-600">Ilustração: as sedes dos ASes brasileiros e os PTTs, com a cor de cada AS pelo que ele anuncia na tabela global (IPv6 e IPv4, só uma das famílias ou nada).</p>
        <HomeMap date={date ?? undefined} title="ASes brasileiros e PTTs" ixpIndex={ixps.data?.ixps} brAsnsInFt={gt?.br_asns_in_ft} />
      </section>
    </div>
  )
}
