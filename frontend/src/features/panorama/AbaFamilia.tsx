// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Kpi } from '../../components/ui'
import { AtribuicaoDbIp } from '../../components/ui/AtribuicaoDbIp'
import { fetchIpv4Espaco, fetchIpv4Mercado, fetchMapPrefixes } from '../../services/api'
import { CartogramaIndicador } from '../estados/CartogramaIndicador'
import { Ipv6Territorio } from '../rede/PanoramaRede'
import { nomeUf } from '../../lib/ufs'
import { CoberturaIxbr } from './CoberturaIxbr'
import { EXPLICA, Ipv6Apnic, useBrasilIndicadores } from './IndicadoresBrasil'
import { SecaoHilbertV4, SecaoHilbertV6 } from './SecoesHilbert'
import { useResumo } from './useResumo'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../lib/ordenacao'
import { fracao, grande, num, pct } from './formato'

export type Familia = 'v6' | 'v4'
const NOME: Record<Familia, string> = { v6: 'IPv6', v4: 'IPv4' }
const UNIDADE: Record<Familia, string> = { v6: '/48', v4: '/24' }

function Secao({ titulo, nota, links = [], children }: { titulo: string; nota?: ReactNode; links?: Array<[string, string]>; children: ReactNode }) {
  return (
    <section className="space-y-3" aria-label={titulo}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 className="text-titulo-3 text-gray-800">{titulo}</h2>
        {links.length > 0 && <p className="flex flex-wrap gap-x-3 text-sm">{links.map(([to, r]) => <Link key={to} to={to} className="text-primario-700 hover:underline">{r} →</Link>)}</p>}
      </div>
      {nota && <p className="text-sm text-gray-600">{nota}</p>}
      {children}
    </section>
  )
}

const Grade = ({ children }: { children: ReactNode }) => <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{children}</div>

/** Usuários: no IPv6 a adoção medida pelo APNIC; no IPv4 não há medida equivalente, então mostra quem não tem IPv6 e o alcance estimado via IX.br. */
function Usuarios({ f }: { f: Familia }) {
  const { data } = useBrasilIndicadores()
  const { summary: s } = useResumo()
  if (f === 'v6') return <Ipv6Apnic />
  const v = data?.ipv6
  const semV6 = v ? v.usuarios - v.usuarios_ipv6 : null
  return (
    <Grade>
      <Kpi rotulo="Usuários sem IPv6 (só IPv4, estimativa)" valor={grande(semV6)} tom="v4" referencia={v?.pct_usuarios_ipv6 != null ? `${pct(100 - v.pct_usuarios_ipv6)} dos usuários estimados` : undefined}
        explicacao={`Usuários estimados pelo APNIC nos ASNs do Brasil menos os que usam IPv6. ${EXPLICA.ipv6}`} fonte="APNIC Labs" dataRef={data?.snapshot_date} />
      <Kpi rotulo="Usuários alcançáveis em IPv4 via IX.br (estimativa)" valor={grande(s?.ixp_estimated_users_v4)} tom="v4"
        explicacao="Usuários estimados do APNIC atrás do espaço IPv4 visto na união dos PTTs do IX.br (fração do espaço de cada AS vista nos PTTs × usuários do AS)." fonte="APNIC Labs e looking glasses do IX.br" dataRef={s?.snapshot_date} />
    </Grade>
  )
}

function Alocacao({ f }: { f: Familia }) {
  const { summary: s } = useResumo()
  const prefixos = f === 'v6' ? s?.registro_br_prefixes_v6 : s?.registro_br_prefixes_v4
  const espaco = f === 'v6' ? s?.registro_br_declared_space_v6_48 : s?.registro_br_declared_space_v4_24
  return (
    <Grade>
      <Kpi rotulo={`Prefixos ${NOME[f]} alocados`} valor={num(prefixos)} tom={f} explicacao={`Blocos ${NOME[f]} alocados ou designados pelo Registro.br a ASNs brasileiros.`} fonte="Registro.br" dataRef={s?.snapshot_date} />
      <Kpi rotulo={`Espaço alocado (${UNIDADE[f]})`} valor={grande(espaco)} tom={f} explicacao={`Soma dos blocos alocados, em equivalentes ${UNIDADE[f]}.`} fonte="Registro.br" dataRef={s?.snapshot_date} />
    </Grade>
  )
}

export function VisibilidadeGlobal({ f }: { f: Familia }) {
  const { summary: s } = useResumo()
  const { data } = useBrasilIndicadores()
  const gt = s?.global_table
  const asns = f === 'v6' ? s?.br_asns_ft_v6 : s?.br_asns_ft_v4
  const rotas = data?.rpki?.rotas?.rotas_br?.[f]
  return (
    <Grade>
      <Kpi rotulo={`ASNs que anunciam ${NOME[f]}`} valor={num(asns)} tom={f} referencia={pct(fracao(asns, gt?.br_asns_in_ft)) ? `${pct(fracao(asns, gt?.br_asns_in_ft))} dos ${num(gt?.br_asns_in_ft)} visíveis` : undefined}
        explicacao={`ASNs do Registro.br com ao menos um prefixo ${NOME[f]} na tabela global (RouteViews).`} fonte="RouteViews e Registro.br" dataRef={s?.snapshot_date} />
      <Kpi rotulo="Espaço alocado visível" valor={pct(f === 'v6' ? gt?.v6_br_coverage_pct : gt?.v4_br_coverage_pct)} tom={f}
        explicacao={`Parte do espaço ${NOME[f]} alocado pelo Registro.br que aparece anunciado na tabela global.`} fonte="RouteViews e Registro.br" dataRef={s?.snapshot_date} />
      <Kpi rotulo="Rotas brasileiras na tabela global" valor={num(rotas?.pbr_routes)} tom={f} referencia={rotas?.pbr_pct != null ? `${pct(rotas.pbr_pct)} das rotas ${NOME[f]} da tabela` : undefined}
        explicacao="Rotas com prefixo alocado pelo Registro.br ou com origem num ASN brasileiro (P_BR, a definição da página Tabela BGP)." fonte="RouteViews e Registro.br" dataRef={data?.rpki?.rotas?.snapshot_date} />
      <Kpi rotulo="Parte do Brasil no espaço da tabela" valor={pct(f === 'v6' ? gt?.v6_br_pct_of_ft : gt?.v4_br_pct_of_ft, 2)} tom={f}
        explicacao={`Parte de todo o espaço ${NOME[f]} anunciado no mundo que é alocado ao Brasil.`} fonte="RouteViews e Registro.br" dataRef={s?.snapshot_date} />
    </Grade>
  )
}

function VisibilidadeIxbr({ f }: { f: Familia }) {
  const { summary: s } = useResumo()
  const ix = s?.ixp_aggregate
  const asns = f === 'v6' ? s?.br_ixp_origin_v6 : s?.br_ixp_origin_v4
  return (
    <div className="space-y-6">
      <Grade>
        <Kpi rotulo={`ASNs BR com rotas ${NOME[f]} vistas no IX.br`} valor={num(asns)} tom={f}
          explicacao="Originam prefixos vistos em algum PTT do IX.br, diretamente ou por um provedor de trânsito." fonte="looking glasses do IX.br" dataRef={s?.snapshot_date} />
        <Kpi rotulo="Espaço alocado visto no IX.br" valor={pct(f === 'v6' ? ix?.v6_br_coverage_pct : ix?.v4_br_coverage_pct)} tom={f}
          explicacao={`Parte do espaço ${NOME[f]} alocado pelo Registro.br que aparece na união dos PTTs do IX.br.`} fonte="looking glasses do IX.br e Registro.br" dataRef={s?.snapshot_date} />
        <Kpi rotulo="Espaço da tabela global visto no IX.br" valor={pct(f === 'v6' ? ix?.v6_coverage_pct : ix?.v4_coverage_pct)} tom={f}
          explicacao={`Parte de todo o espaço ${NOME[f]} da tabela global que aparece na união dos PTTs do IX.br.`} fonte="looking glasses do IX.br e RouteViews" dataRef={s?.snapshot_date} />
      </Grade>
      <CoberturaIxbr grupos={[f === 'v6' ? 'ipv6' : 'ipv4']} />
    </div>
  )
}

/** Estado RPKI das rotas da família e o espaço anunciado por ASes com ROA (rótulo exato: não é espaço coberto por ROA). */
function Rpki({ f }: { f: Familia }) {
  const { data } = useBrasilIndicadores()
  const r = data?.rpki?.rotas?.rpki?.[f]
  const pub = data?.rpki?.publicacao
  const anunciado = f === 'v6' ? [pub?.br_space_v6_roa_48, pub?.br_space_v6_total_48] : [pub?.br_space_v4_roa_24, pub?.br_space_v4_total_24]
  const ref = data?.rpki?.rotas?.snapshot_date
  return (
    <Grade>
      <Kpi rotulo="Rotas RPKI-válidas" valor={pct(r?.pct.valid)} tom="tecnico" referencia={r ? `${num(r.valid)} de ${num(r.rotas)} rotas` : undefined} explicacao="Origem confirmada por uma ROA (RFC 6811)." fonte="RouteViews e RPKI" dataRef={ref} />
      <Kpi rotulo="Rotas RPKI-inválidas" valor={pct(r?.pct.invalid, 2)} tom="tecnico" referencia={r ? `${num(r.invalid)} rotas, ${num(r.asns_origem_com_invalida)} ASNs de origem` : undefined}
        explicacao="Há ROA para o prefixo, mas a origem ou o tamanho não batem: redes que validam (ROV) descartam a rota." fonte="RouteViews e RPKI" dataRef={ref} />
      <Kpi rotulo="Rotas sem ROA" valor={pct(r?.pct.not_found)} tom="tecnico" referencia={r ? `${num(r.not_found)} rotas` : undefined} explicacao="Nenhuma ROA cobre o prefixo: não é inválido, só não está protegido." fonte="RouteViews e RPKI" dataRef={ref} />
      <Kpi rotulo="Espaço anunciado por ASes com ROA" valor={pct(fracao(anunciado[0], anunciado[1]))} tom="tecnico"
        explicacao="Espaço anunciado pelos ASNs BR que publicaram ao menos uma ROA. Não é o espaço coberto por ROA: um AS com uma ROA pode anunciar outros prefixos sem ela." fonte="RPKI e RouteViews" dataRef={data?.snapshot_date} />
    </Grade>
  )
}

interface FeicaoPrefixo { properties: { uf?: string; ip_version?: number; prefix_count?: number } }

/** Prefixos da família geolocalizados por UF (o mapa de prefixos do site, já agregado por AS e município). */
function PrefixosPorUf({ f }: { f: Familia }) {
  const { date } = useResumo()
  const q = useQuery({ queryKey: ['map-prefixes', date], queryFn: () => fetchMapPrefixes(date ?? undefined) as Promise<{ features: FeicaoPrefixo[] }>, staleTime: Infinity, gcTime: Infinity, retry: false })
  const versao = f === 'v6' ? 6 : 4
  const porUf: Record<string, number> = {}
  for (const ft of q.data?.features ?? []) {
    const uf = (ft.properties.uf || '').toUpperCase()
    if (!uf || (ft.properties.ip_version === 6) !== (versao === 6)) continue
    porUf[uf] = (porUf[uf] ?? 0) + (ft.properties.prefix_count ?? 1)
  }
  const { ordenados: linhas, props } = useOrdenacao(Object.entries(porUf).sort((a, b) => b[1] - a[1]), { uf: ([uf]) => uf, prefixos: ([, n]) => n })
  if (q.isLoading) return <div className="h-40 animate-pulse rounded bg-gray-50" />
  if (!q.data) return <p className="text-sm text-gray-500">A geolocalização dos prefixos não está disponível.</p>
  return (
    <CartogramaIndicador titulo={`Prefixos ${NOME[f]} geolocalizados, por UF`} indicadores={[{ id: f, rotulo: 'Prefixos', valor: (uf) => porUf[uf] ?? null, texto: (v) => v.toLocaleString('pt-BR') }]}
      verDados={<table className="text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><ThOrdenavel {...props('uf')} className="px-2 py-1 text-left">UF</ThOrdenavel><ThOrdenavel {...props('prefixos')} alinhar="right" className="px-2 py-1 text-right">Prefixos {NOME[f]}</ThOrdenavel></tr></thead>
        <tbody>{linhas.map(([uf, n]) => <tr key={uf} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf} — {nomeUf(uf)}</Link></td><td className="px-2 py-1 text-right tabular-nums">{n.toLocaleString('pt-BR')}</td></tr>)}</tbody></table>} />
  )
}

/** Mercado secundário de IPv4: só os totais, o detalhe fica em /mercado-ipv4. */
function MercadoIpv4() {
  const mercado = useQuery({ queryKey: ['ipv4-mercado'], queryFn: fetchIpv4Mercado, staleTime: 10 * 60 * 1000, retry: false })
  const espaco = useQuery({ queryKey: ['ipv4-espaco-resumo'], queryFn: () => fetchIpv4Espaco({ limit: 1 }), staleTime: 10 * 60 * 1000, retry: false })
  const m = mercado.data
  const naoAnunciado = espaco.data?.resumo.por_classe?.nao_anunciado
  if (mercado.isError && espaco.isError) return <p className="text-sm text-gray-500">O mercado de IPv4 não está publicado neste snapshot.</p>
  return (
    <Grade>
      <Kpi rotulo="Transferências com o Brasil" valor={num(m?.operacoes)} tom="v4" referencia={m?.periodo?.[0] ? `de ${m.periodo[0]} a ${m.periodo[1] ?? 'hoje'}` : undefined} fonte={m?.fonte} dataRef={m?.snapshot_date} />
      <Kpi rotulo="Endereços transferidos" valor={grande(m?.enderecos)} tom="v4" fonte={m?.fonte} dataRef={m?.snapshot_date} />
      <Kpi rotulo="Endereços alocados não anunciados" valor={grande(naoAnunciado?.enderecos)} tom="v4" referencia={naoAnunciado ? `${num(naoAnunciado.blocos)} blocos` : undefined}
        explicacao="Blocos do Brasil que não aparecem na tabela global. Inferido: não anunciado não quer dizer sem uso (pode ser rede interna)." fonte={espaco.data?.fonte} dataRef={espaco.data?.snapshot_date} />
    </Grade>
  )
}

/**
 * Abas IPv6 e IPv4 do Panorama técnico: a mesma sequência nas duas famílias, de quem usa ao espaço — usuários, alocação,
 * visibilidade na tabela global, visibilidade no IX.br (agregado e por PTT), RPKI, território e o espaço
 * em curva de Hilbert. O IPv4 não tem medida de adoção pelos usuários equivalente à do APNIC, e ganha o mercado secundário no lugar.
 */
export function AbaFamilia({ familia: f }: { familia: Familia }) {
  const n = NOME[f]
  return (
    <div className="space-y-10" data-testid={`aba-${f === 'v6' ? 'ipv6' : 'ipv4'}`}>
      <Secao titulo="Usuários">{<Usuarios f={f} />}</Secao>
      <Secao titulo="Alocação" nota={`O que o Registro.br alocou em ${n} a ASNs brasileiros.`}><Alocacao f={f} /></Secao>
      <Secao titulo="Visibilidade na tabela global" links={[['/bgp', 'Tabela BGP'], ['/bgp?aba=agregacao', 'Cobertura dos blocos']]}><VisibilidadeGlobal f={f} /></Secao>
      <Secao titulo="Visibilidade no IX.br" links={[['/ixps', 'PTTs']]}><VisibilidadeIxbr f={f} /></Secao>
      <Secao titulo="RPKI" links={[['?aba=seguranca', 'Segurança']]} nota={`Estado RPKI de origem das rotas brasileiras ${n} na tabela global.`}><Rpki f={f} /></Secao>
      {f === 'v4' && <Secao titulo="Mercado secundário" links={[['/mercado-ipv4', 'Mercado IPv4']]}><MercadoIpv4 /></Secao>}
      <Secao titulo="No território" nota={f === 'v6' ? 'Acessos em IPv6 estimados por UF e município (acessos do SICI × adoção de IPv6 do AS), e os prefixos IPv6 geolocalizados.' : 'Prefixos IPv4 geolocalizados, pela localização do AS e dos prefixos.'}>
        {f === 'v6' && <Ipv6Territorio />}
        <PrefixosPorUf f={f} />
        <AtribuicaoDbIp className="mt-2" />
      </Secao>
      <section aria-label={`Espaço ${n}`}>{f === 'v6' ? <SecaoHilbertV6 /> : <SecaoHilbertV4 />}</section>
    </div>
  )
}
