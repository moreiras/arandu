// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchRedeTerritorio } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { CartogramaIndicador } from '../estados/CartogramaIndicador'
import { MapaSobDemanda } from '../estados/MapaSobDemanda'
import { INDICADORES_REDE } from '../../lib/indicadoresMapa'
import { nomeUf } from '../../lib/ufs'
import type { ResumoRedeTerritorio } from '../../types/api'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../lib/ordenacao'
import { AvisosRecorte, textoPeso } from '../../components/ui/AvisoRecorte'

const p = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

function useRede() {
  const date = useActiveDate()
  return useQuery({ queryKey: ['rede-territorio', date], queryFn: () => fetchRedeTerritorio(date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
}

function Estado({ q, children }: { q: ReturnType<typeof useRede>; children: (d: ResumoRedeTerritorio) => React.ReactNode }) {
  if (q.isLoading) return <div className="h-40 bg-gray-50 rounded animate-pulse" />
  if (!q.data) return <p className="text-sm text-gray-500">A rede no território não está publicada neste snapshot.</p>
  return <>{children(q.data)}</>
}

const Rodape = ({ d }: { d: ResumoRedeTerritorio }) => <p className="text-xs text-gray-500">{d.limites} Snapshot {d.snapshot_date}.</p>

// "Ver dados" de cada cartograma: as 27 UFs inteiras, ordenáveis por coluna (componentes próprios porque o conteúdo vem de render prop).
function DadosIpv6({ ufs }: { ufs: ResumoRedeTerritorio['ipv6']['ufs'] }) {
  const { ordenados, props } = useOrdenacao(Object.entries(ufs), { uf: ([uf]) => uf, v6: ([, v]) => v.pct_v6, cobertura: ([, v]) => v.cobertura })
  return (
    <table className="text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><ThOrdenavel {...props('uf')} className="px-2 py-1 text-left">UF</ThOrdenavel><ThOrdenavel {...props('v6')} alinhar="right" className="px-2 py-1 text-right">IPv6 estimado</ThOrdenavel><ThOrdenavel {...props('cobertura')} alinhar="right" className="px-2 py-1 text-right">Cobertura</ThOrdenavel></tr></thead>
      <tbody>{ordenados.map(([uf, v]) => <tr key={uf} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf} — {nomeUf(uf)}</Link></td><td className="px-2 py-1 text-right tabular-nums">{p(v.pct_v6)}</td><td className="px-2 py-1 text-right tabular-nums">{p(v.cobertura)}</td></tr>)}</tbody></table>
  )
}

function DadosRov({ ufs }: { ufs: ResumoRedeTerritorio['rov']['ufs'] }) {
  const { ordenados, props } = useOrdenacao(Object.entries(ufs), { uf: ([uf]) => uf, rov: ([, v]) => v.pct_atras_rov, usuarios: ([, v]) => v.usuarios_com_medida, cobertura: ([, v]) => v.cobertura })
  return (
    <table className="text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><ThOrdenavel {...props('uf')} className="px-2 py-1 text-left">UF</ThOrdenavel><ThOrdenavel {...props('rov')} alinhar="right" className="px-2 py-1 text-right">Atrás de ROV</ThOrdenavel><ThOrdenavel {...props('usuarios')} alinhar="right" className="px-2 py-1 text-right">Usuários com medida</ThOrdenavel><ThOrdenavel {...props('cobertura')} alinhar="right" className="px-2 py-1 text-right">Cobertura</ThOrdenavel><th scope="col" className="px-2 py-1 text-right">ASNs com medida</th><th scope="col" className="px-2 py-1 text-right">Maior ASN</th><th scope="col" className="px-2 py-1 text-left">Aviso</th></tr></thead>
      <tbody>{ordenados.map(([uf, v]) => <tr key={uf} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf} — {nomeUf(uf)}</Link></td><td className="px-2 py-1 text-right tabular-nums">{p(v.pct_atras_rov)}</td><td className="px-2 py-1 text-right tabular-nums">{v.usuarios_com_medida.toLocaleString('pt-BR')}</td><td className="px-2 py-1 text-right tabular-nums">{p(v.cobertura)}</td><td className="px-2 py-1 text-right tabular-nums">{v.n_asns_com_dado?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{textoPeso(v.peso_top1)?.replace('maior: ', '') ?? '—'}</td><td className="px-2 py-1"><AvisosRecorte avisos={v.avisos} /></td></tr>)}</tbody></table>
  )
}

function DadosTransito({ ufs }: { ufs: ResumoRedeTerritorio['transito']['ufs'] }) {
  const { ordenados, props } = useOrdenacao(Object.entries(ufs), {
    uf: ([uf]) => uf, unico: ([, v]) => v.pct_provedor_unico, cobertura: ([, v]) => v.cobertura,
    provedor: ([, v]) => (v.provedor_principal ? (v.provedor_principal.nome || `AS${v.provedor_principal.asn}`) : null),
  })
  return (
    <table className="text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><ThOrdenavel {...props('uf')} className="px-2 py-1 text-left">UF</ThOrdenavel><ThOrdenavel {...props('unico')} alinhar="right" className="px-2 py-1 text-right">Um só provedor</ThOrdenavel><ThOrdenavel {...props('cobertura')} alinhar="right" className="px-2 py-1 text-right">Cobertura</ThOrdenavel><ThOrdenavel {...props('provedor')} className="px-2 py-1 text-left">Provedor mais comum</ThOrdenavel></tr></thead>
      <tbody>{ordenados.map(([uf, v]) => <tr key={uf} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf}</Link></td><td className="px-2 py-1 text-right tabular-nums">{p(v.pct_provedor_unico)}</td><td className="px-2 py-1 text-right tabular-nums">{p(v.cobertura)}</td><td className="px-2 py-1">{v.provedor_principal ? (v.provedor_principal.nome || `AS${v.provedor_principal.asn}`) : '—'}</td></tr>)}</tbody></table>
  )
}

/** IPv6 estimado por UF e por município (Panorama de IPv6). Estimativa: supõe a mesma adoção do AS em todos os municípios da operadora; a cobertura vem junto. */
export function Ipv6Territorio() {
  const q = useRede()
  return (
    <Estado q={q}>{(d) => (
      <div className="space-y-4" data-testid="ipv6-territorio">
        <p className="text-sm text-gray-700">Estimativa: cerca de <strong>{p(d.ipv6.brasil.pct_v6)}</strong> dos acessos fixos declarados estão em operadoras com IPv6 medido pela APNIC, ponderados pela adoção de cada AS (cobertura {p(d.ipv6.brasil.cobertura)} dos acessos).</p>
        <CartogramaIndicador titulo="Acessos em IPv6, por UF (estimativa)" indicadores={[{ id: 'v6', rotulo: 'IPv6 (%)', valor: (uf) => d.ipv6.ufs[uf]?.pct_v6 ?? null, texto: (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`, maximo: 100 }]}
          verDados={<DadosIpv6 ufs={d.ipv6.ufs} />} />
        <MapaSobDemanda indicadores={INDICADORES_REDE.slice(0, 1)} titulo="Mapa dos municípios: IPv6 estimado" chamada="Os municípios coloridos pela estimativa de acessos em IPv6. Carrega cerca de 0,5 MB." />
        <Rodape d={d} />
      </div>
    )}</Estado>
  )
}

/** Usuários atrás de ASNs que validam ROV, por UF da sede do ASN (Segurança de roteamento). */
export function RovTerritorio() {
  const q = useRede()
  return (
    <Estado q={q}>{(d) => (
      <div className="space-y-4" data-testid="rov-territorio">
        <p className="text-sm text-gray-700">Estimativa: cerca de <strong>{p(d.rov.brasil.pct_atras_rov)}</strong> dos usuários estimados (com medida) estão em ASNs que validam ROV — {d.rov.brasil.usuarios_atras_rov.toLocaleString('pt-BR')} de {d.rov.brasil.usuarios_com_medida.toLocaleString('pt-BR')}; a medida cobre {p(d.rov.brasil.cobertura)} dos {d.rov.brasil.usuarios.toLocaleString('pt-BR')} usuários. Só entram ASNs com pelo menos {d.rov.parametros.min_amostras} amostras da APNIC; a UF é a da sede do ASN, não a dos usuários.</p>
        <CartogramaIndicador titulo="Usuários atrás de ROV, por UF (estimativa)" indicadores={[{ id: 'rov', rotulo: 'Atrás de ROV (%)', valor: (uf) => d.rov.ufs[uf]?.pct_atras_rov ?? null, texto: (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`, maximo: 100 }]}
          verDados={<DadosRov ufs={d.rov.ufs} />} />
        <Rodape d={d} />
      </div>
    )}</Estado>
  )
}

/** Dependência de trânsito da região: parcela dos acessos com um único provedor inferido, por UF e município. */
export function TransitoTerritorio() {
  const q = useRede()
  return (
    <Estado q={q}>{(d) => (
      <div className="space-y-4" data-testid="transito-territorio">
        <CartogramaIndicador titulo="Acessos com um só provedor de trânsito, por UF (inferido)" indicadores={[{ id: 'tr', rotulo: 'Um só provedor (%)', valor: (uf) => d.transito.ufs[uf]?.pct_provedor_unico ?? null, texto: (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`, maximo: 100 }]}
          verDados={<DadosTransito ufs={d.transito.ufs} />} />
        <MapaSobDemanda indicadores={INDICADORES_REDE.slice(1)} titulo="Mapa dos municípios: dependência de trânsito" chamada="Os municípios coloridos pela parcela dos acessos com um único provedor de trânsito inferido. Carrega cerca de 0,5 MB." />
        <Rodape d={d} />
      </div>
    )}</Estado>
  )
}
