// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { useQuery } from '@tanstack/react-query'
import { useHistoricoCompleto } from '../../hooks/entidades/entidades'
import { fetchAlcanceCdns, fetchAsnCdnBrasil, type AsnCdnBrasil } from '../../services/api'
import { CartogramaIndicador } from '../estados/CartogramaIndicador'

const n = (v: number) => v.toLocaleString('pt-BR')

/** Soma, por PTT do IX.br e família de IP, os prefixos que os ASNs da CDN anunciam ali (peering direto observado) e a série de PTTs com peering direto. */
export function agregarCdnBrasil(docs: AsnCdnBrasil[], ixbr: string[]) {
  const por: Record<string, { v4: number; v6: number }> = {}
  for (const d of docs) for (const [code, p] of Object.entries(d.ixp_peers ?? {})) {
    if (!ixbr.includes(code)) continue
    const l = (por[code] ??= { v4: 0, v6: 0 })
    l.v4 += p.v4?.total_prefixes ?? 0; l.v6 += p.v6?.total_prefixes ?? 0
  }
  const serie = new Map<string, number>()
  for (const d of docs) for (const pt of d.historico?.serie ?? []) {
    const v = pt['n_ixd']; if (typeof v === 'number') serie.set(pt.date, Math.max(serie.get(pt.date) ?? 0, v))
  }
  return {
    linhas: Object.entries(por).map(([code, v]) => ({ code, ...v })).sort((a, b) => b.v4 + b.v6 - (a.v4 + a.v6) || a.code.localeCompare(b.code)),
    serie: Array.from(serie.entries()).sort(([a], [b]) => a.localeCompare(b)),
  }
}

/**
 * A CDN sob a ótica brasileira: em quais PTTs do IX.br ela tem peering direto, quantos prefixos anuncia ali em IPv6 e IPv4 (só contagens, nunca a lista) e como o
 * número de PTTs variou entre snapshots. O histórico começou em 2026-10 e o anônimo só vê as datas atuais. Quais ASes BR recebem as rotas da CDN nos route servers
 * não está nos dados coletados (precisaria das rotas do Alice por origem) e por isso não aparece.
 */
/** Alcance da CDN por peering: a fração dos usuários BR em ASes membros dos PTTs onde ela está, por UF. Estimativa; não mede tráfego. */
function Alcance({ nome, date }: { nome: string; date: string | null }) {
  const q = useQuery({ queryKey: ['cdns-alcance', date], queryFn: () => fetchAlcanceCdns(date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
  const c = q.data?.cdns.find((x) => x.name === nome)
  if (!c) return null
  const p = (v: number | null) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
  return (
    <div className="space-y-2" data-testid="alcance-cdn">
      <h3 className="text-sm font-medium text-gray-700">Alcance por peering (estimativa): {p(c.pct)} dos usuários BR</h3>
      <CartogramaIndicador indicadores={[{ id: 'alc', rotulo: 'Alcance (%)', valor: (uf) => c.por_uf[uf]?.pct ?? null, texto: (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`, maximo: 100 }]} />
      <p className="text-xs text-gray-500">{q.data!.limites}</p>
    </div>
  )
}

type Props = { asns: number[]; ixbr: string[]; ixpNames: Record<string, string>; date: string | null; nome?: string }

/** Só busca o perfil de cada ASN da CDN quando a pessoa abre a seção (a CDN com mais ASNs custaria 15 chamadas a mais ao abrir a página). */
export function VisaoBrasil(props: Props) {
  const [aberto, setAberto] = useState(false)
  if (!aberto) {
    return (
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white p-4" data-testid="cdn-brasil-fechado">
        <div><h2 className="text-base font-semibold text-gray-800">No Brasil: PTTs do IX.br, prefixos anunciados e alcance</h2><p className="text-sm text-gray-500">Presença por PTT e família de IP, evolução e alcance por UF.</p></div>
        <button type="button" onClick={() => setAberto(true)} className="rounded-md bg-primario-600 px-3 py-1.5 text-sm text-white hover:bg-primario-700">Mostrar</button>
      </section>
    )
  }
  return <VisaoBrasilAberta {...props} />
}

function VisaoBrasilAberta({ asns, ixbr, ixpNames, date, nome }: Props) {
  const completo = useHistoricoCompleto()
  const qs = useQueries({ queries: asns.map((a) => ({ queryKey: ['cdn-br', a, date, completo], queryFn: () => fetchAsnCdnBrasil(a, date ?? undefined, completo), staleTime: 10 * 60 * 1000 })) })
  const docs = qs.map((q) => q.data).filter((d): d is AsnCdnBrasil => !!d)
  const { linhas, serie } = useMemo(() => agregarCdnBrasil(docs, ixbr), [docs.length, ixbr.join(',')])   // eslint-disable-line react-hooks/exhaustive-deps
  if (qs.some((q) => q.isLoading) && docs.length === 0) return <div className="h-24 bg-gray-50 rounded animate-pulse" />
  return (
    <section className="space-y-3" data-testid="cdn-brasil">
      <h2 className="text-base font-semibold text-gray-800">No Brasil: PTTs do IX.br e prefixos anunciados</h2>
      {linhas.length === 0 ? <p className="text-sm text-gray-500">Sem prefixos anunciados por esta CDN nos PTTs do IX.br neste snapshot.</p> : (
        <div className="overflow-x-auto"><table className="min-w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><th className="py-1 pr-3 font-medium">PTT</th><th className="py-1 pr-3 font-medium text-right">Prefixos IPv6</th><th className="py-1 pr-3 font-medium text-right">Prefixos IPv4</th></tr></thead>
          <tbody>{linhas.map((l) => (
            <tr key={l.code} className="border-b border-gray-100">
              <td className="py-1 pr-3"><Link to={`/ixp/${l.code}`} className="text-primario-700 hover:underline">{ixpNames[l.code] ?? l.code}</Link></td>
              <td className="py-1 pr-3 text-right tabular-nums">{l.v6 ? n(l.v6) : '—'}</td><td className="py-1 pr-3 text-right tabular-nums">{l.v4 ? n(l.v4) : '—'}</td>
            </tr>))}</tbody>
        </table></div>
      )}
      {nome && <Alcance nome={nome} date={date} />}
      <p className="text-xs text-gray-500">
        {serie.length > 1
          ? <>PTTs com peering direto: {serie.map(([d, v]) => `${d}: ${v}`).join(' · ')}.</>
          : 'Evolução: o histórico ainda tem um só snapshot visível (ele começou em 2026-10; sem login só aparecem as datas atuais).'}
        {' '}Contagens de prefixos vistos nas rotas coletadas por PTT; não medem tráfego. Os ASes BR que recebem as rotas da CDN nos route servers não são coletados.
      </p>
    </section>
  )
}
