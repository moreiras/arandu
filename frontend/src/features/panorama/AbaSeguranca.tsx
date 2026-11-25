// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ComoLer, Kpi } from '../../components/ui'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../../components/ui/EstadoDados'
import { SegurancaSection } from '../../components/stats/SegurancaSection'
import { fetchProntidaoResumo } from '../../services/api'
import type { EstadoRpkiFamilia } from '../../types/api'
import { AbaDnssec, AbaProntidao, EXPLICA, useBrasilIndicadores } from './IndicadoresBrasil'
import { useResumo } from './useResumo'
import { fracao, grande, num, pct } from './formato'

function Secao({ id, titulo, links = [], children }: { id: string; titulo: string; links?: Array<[string, string]>; children: ReactNode }) {
  return (
    <section id={id} className="space-y-3 scroll-mt-20" aria-label={titulo}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 className="text-titulo-3 text-gray-800">{titulo}</h2>
        {links.length > 0 && <p className="flex flex-wrap gap-x-3 text-sm">{links.map(([to, r]) => <Link key={to} to={to} className="text-primario-700 hover:underline">{r} →</Link>)}</p>}
      </div>
      {children}
    </section>
  )
}

const Grade = ({ children }: { children: ReactNode }) => <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{children}</div>

/** Publicação no RPKI: quantos ASNs do Brasil têm ROA e ASPA (também em /seguranca-de-roteamento). */
export function RpkiPublicacao() {
  const { data } = useBrasilIndicadores()
  const p = data?.rpki?.publicacao
  const ref = data?.snapshot_date
  return (
    <Grade>
      <Kpi rotulo="ASNs com ROA" valor={pct(fracao(p?.br_asns_with_roa, p?.br_asns_total))} tom="tecnico" referencia={p ? `${num(p.br_asns_with_roa)} de ${num(p.br_asns_total)} ASNs` : undefined}
        explicacao="ASNs do Registro.br que publicaram ao menos uma ROA (autorização de origem) no RPKI." fonte="RPKI (Routinator)" dataRef={ref} />
      <Kpi rotulo="ASNs com ASPA" valor={pct(fracao(p?.br_asns_with_aspa, p?.br_asns_total))} tom="tecnico" referencia={p ? `${num(p.br_asns_with_aspa)} ASNs` : undefined}
        explicacao="ASNs do Registro.br que publicaram um objeto ASPA (a lista dos provedores de trânsito autorizados do AS)." fonte="RPKI (Routinator)" dataRef={ref} />
      <Kpi rotulo="Espaço IPv6 anunciado por ASes com ROA" valor={pct(fracao(p?.br_space_v6_roa_48, p?.br_space_v6_total_48))} tom="v6"
        explicacao="Espaço IPv6 anunciado pelos ASNs BR que publicaram ao menos uma ROA. Não é o espaço coberto por ROA; esse está no estado das rotas, abaixo." fonte="RPKI e RouteViews" dataRef={ref} />
      <Kpi rotulo="Espaço IPv4 anunciado por ASes com ROA" valor={pct(fracao(p?.br_space_v4_roa_24, p?.br_space_v4_total_24))} tom="v4"
        explicacao="Espaço IPv4 anunciado pelos ASNs BR que publicaram ao menos uma ROA. Não é o espaço coberto por ROA; esse está no estado das rotas, abaixo." fonte="RPKI e RouteViews" dataRef={ref} />
    </Grade>
  )
}

function Celula({ n, p }: { n: number; p: number | null }) {
  return <td className="px-2 py-1 text-right tabular-nums">{n.toLocaleString('pt-BR')}<span className="block text-xs text-gray-500">{pct(p, 2) ?? '—'}</span></td>
}

/** Estado RPKI de origem das rotas brasileiras por família (também em /seguranca-de-roteamento). */
export function EstadoRpkiRotas() {
  const { data, isLoading } = useBrasilIndicadores()
  if (isLoading) return <div className="h-24 animate-pulse rounded bg-gray-100" />
  const r = data?.rpki?.rotas
  if (!r) return <p className="text-sm text-gray-500">O estado RPKI das rotas não foi calculado para este snapshot.</p>
  const linhas: Array<['IPv6' | 'IPv4', EstadoRpkiFamilia]> = [['IPv6', r.rpki.v6], ['IPv4', r.rpki.v4]]
  return (
    <div className="space-y-3" data-testid="estado-rpki-rotas">
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full text-sm" aria-label="Rotas brasileiras por estado RPKI">
          <thead className="bg-gray-50 text-xs text-gray-600">
            <tr><th className="px-2 py-1 text-left">Família</th><th className="px-2 py-1 text-right">Rotas</th><th className="px-2 py-1 text-right">Válidas</th><th className="px-2 py-1 text-right">Inválidas</th><th className="px-2 py-1 text-right">Sem ROA</th>
              <th className="px-2 py-1 text-right">Espaço válido</th><th className="px-2 py-1 text-right">Espaço inválido</th><th className="px-2 py-1 text-right">Espaço sem ROA</th><th className="px-2 py-1 text-right">ASNs com rota inválida</th></tr>
          </thead>
          <tbody>
            {linhas.map(([nome, e]) => (
              <tr key={nome} className="border-t border-gray-100">
                <th scope="row" className="px-2 py-1 text-left font-medium">{nome}</th>
                <td className="px-2 py-1 text-right tabular-nums">{e.rotas.toLocaleString('pt-BR')}</td>
                <Celula n={e.valid} p={e.pct.valid} /><Celula n={e.invalid} p={e.pct.invalid} /><Celula n={e.not_found} p={e.pct.not_found} />
                {(['valid', 'invalid', 'not_found'] as const).map((k) => <td key={k} className="px-2 py-1 text-right tabular-nums">{pct(fracao(e.espaco[k], e.espaco.total), k === 'invalid' ? 2 : 1)}<span className="block text-xs text-gray-500">{grande(e.espaco[k])} {e.espaco.unidade}</span></td>)}
                <td className="px-2 py-1 text-right tabular-nums">{e.asns_origem_com_invalida.toLocaleString('pt-BR')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ComoLer>
        <p>{r.definicao} Válida: uma ROA cobre o prefixo com a mesma origem e tamanho permitido. Inválida: há ROA, mas a origem ou o tamanho não batem, e redes que fazem ROV descartam a rota. Sem ROA: nenhuma ROA cobre o prefixo.</p>
        <p>{r.limites} {r.vrps != null ? `VRPs do snapshot: ${r.vrps.toLocaleString('pt-BR')}.` : ''} Snapshot {r.snapshot_date}.</p>
      </ComoLer>
    </div>
  )
}

function Rov() {
  const { data } = useBrasilIndicadores()
  const r = data?.rov
  const ref = r?.fonte?.as_of ?? data?.snapshot_date
  if (data && !r) return <p className="text-sm text-gray-500">Medição de ROV não publicada neste snapshot.</p>
  return (
    <div className="space-y-4">
      <Grade>
        <Kpi rotulo="Filtragem de rotas inválidas (média ponderada)" valor={pct(r?.media_ponderada_pct)} tom="tecnico" explicacao={EXPLICA.rov} fonte="APNIC Labs" dataRef={ref} />
        <Kpi rotulo="Mediana dos ASes" valor={pct(r?.mediana_pct)} tom="tecnico" explicacao="Metade dos ASNs medidos filtra em menos que isso. Cada ASN conta igual." fonte="APNIC Labs" dataRef={ref} />
        <Kpi rotulo="ASes medidos" valor={num(r?.asns)} tom="tecnico" explicacao="ASNs do Brasil com amostra suficiente na medição do APNIC." fonte="APNIC Labs" dataRef={ref} />
      </Grade>
      <SegurancaSection date={data?.snapshot_date} semResumo />
    </div>
  )
}

function SaudeTabela() {
  const { data } = useBrasilIndicadores()
  const { summary } = useResumo()
  // MOAS fica na aba MOAS de /bgp (`saude.moas` existe no resumo, mas a leitura pede a lista e o "como ler" ao lado).
  const sa = data?.rpki?.rotas?.saude
  const bogon = data?.prontidao?.agregado.medicoes?.sem_bogon
  const ref = data?.rpki?.rotas?.snapshot_date ?? summary?.snapshot_date
  return (
    <Grade>
      <Kpi rotulo="Rotas mais-específicas (IPv6 · IPv4)" valor={sa ? `${pct(sa.v6.mais_especificos_pct) ?? '—'} · ${pct(sa.v4.mais_especificos_pct) ?? '—'}` : null}
        explicacao="Rotas brasileiras contidas em outra rota anunciada (desagregação). Nem sempre é problema: pode ser engenharia de tráfego." fonte="RouteViews" dataRef={ref} />
      <Kpi rotulo="Prefixos filtráveis (IPv6 · IPv4)" valor={sa ? `${num(sa.v6.filtraveis) ?? '—'} · ${num(sa.v4.filtraveis) ?? '—'}` : null}
        explicacao="Mais específicos que /48 (IPv6) ou /24 (IPv4): muitas redes descartam esses prefixos." fonte="RouteViews" dataRef={ref} />
      <Kpi rotulo="ASes sem bogon" valor={pct(bogon?.media)} referencia={bogon ? `entre ${num(bogon.asns)} ASNs com ROV medido` : undefined}
        explicacao="Parte dos ASNs que não originam prefixo reservado ou não alocado. Só existe para os ASNs com ROV medido (componente do índice de prontidão)." fonte="RouteViews e listas de bogons" dataRef={data?.snapshot_date} />
    </Grade>
  )
}

function Manrs() {
  const q = useQuery({ queryKey: ['prontidao-resumo'], queryFn: () => fetchProntidaoResumo(), staleTime: 10 * 60 * 1000, retry: false })
  const m = q.data?.manrs
  // Sem resposta por acesso, taxa ou rede o bloco avisa em vez de sumir (sumir parece "sem MANRS no snapshot").
  if (q.isError && ehErroDeAcessoOuFalha(q.error)) return <EstadoDados erro={q.error} oQue="a participação no MANRS" />
  if (!m || m.brasil.suprimido) return null
  const b = m.brasil
  return (
    <div className="space-y-1">
      <Grade>
        <Kpi rotulo="ASNs em organizações do MANRS" valor={pct(b.pct_asns)} tom="tecnico" referencia={`${num(b.asns_participantes)} de ${num(b.asns)} ASNs`} fonte={m.fonte.descricao} dataRef={m.fonte.medido_em ?? m.snapshot_date} />
        <Kpi rotulo="Usuários nesses ASNs" valor={pct(b.pct_usuarios)} tom="tecnico" explicacao="Usuários estimados pelo APNIC nos ASNs de organizações participantes." fonte="MANRS e APNIC Labs" dataRef={m.fonte.medido_em ?? m.snapshot_date} />
      </Grade>
      <p className="text-xs text-gray-500">{m.atribuicao}.</p>
    </div>
  )
}

/**
 * Aba Segurança do Panorama técnico: junta Segurança de roteamento, Prontidão e DNSSEC. Primeiro o que está publicado
 * no RPKI (ROA, ASPA) e o efeito nas rotas (válidas, inválidas, sem ROA); depois quem filtra (ROV), a saúde da tabela, o índice de prontidão e o DNSSEC.
 * O detalhe por UF e porte, os mapas e a metodologia ficam em /seguranca-de-roteamento.
 */
export function AbaSeguranca() {
  const detalhe: Array<[string, string]> = [['/seguranca-de-roteamento', 'Por UF e porte']]
  return (
    <div className="space-y-10" data-testid="aba-seguranca">
      <Secao id="rpki" titulo="RPKI: publicação (ROA e ASPA)" links={detalhe}><RpkiPublicacao /></Secao>
      <Secao id="rotas" titulo="RPKI: estado das rotas brasileiras"><EstadoRpkiRotas /></Secao>
      <Secao id="rov" titulo="ROV: redes que descartam rotas inválidas" links={[['/seguranca-de-roteamento', 'Usuários atrás de ROV, por UF']]}><Rov /></Secao>
      <Secao id="saude" titulo="Saúde da tabela" links={[['/bgp', 'Tabela BGP']]}><SaudeTabela /></Secao>
      <Secao id="prontidao" titulo="Prontidão em segurança de roteamento" links={detalhe}><AbaProntidao /><Manrs /></Secao>
      <Secao id="dnssec" titulo="DNSSEC"><AbaDnssec /></Secao>
    </div>
  )
}
