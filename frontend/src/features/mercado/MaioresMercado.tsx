// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ResponsiveContainer, Treemap } from 'recharts'
import { fetchMercadoMaiores } from '../../services/api'
import { useResumo } from '../panorama/useResumo'
import { BumpChart } from './BumpChart'

const COR_GRUPO = '#2563eb', COR_CNPJ = '#6b7280', COR_DEMAIS = '#d1d5db'
const pct = (v: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%')

/** Célula do treemap: o rótulo só aparece onde cabe (o que não cabe está na tabela logo abaixo). */
function Celula(p: { x?: number; y?: number; width?: number; height?: number; name?: string; cor?: string; share?: number | null }) {
  const { x = 0, y = 0, width = 0, height = 0, name = '', cor = COR_CNPJ, share } = p
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={cor} stroke="#fff" strokeWidth={2} />
      {width > 70 && height > 34 && <text x={x + 6} y={y + 17} fontSize="12" fill={cor === COR_DEMAIS ? '#1f2937' : '#fff'}>{name.length > Math.floor(width / 7) ? name.slice(0, Math.max(3, Math.floor(width / 7) - 1)) + '…' : name}<tspan x={x + 6} dy="15" fontSize="11">{pct(share ?? null)}</tspan></text>}
    </g>
  )
}

/** Maiores do mercado fixo (Panorama de mercado): bump chart das maiores operadoras e treemap por empresa ou grupo (inferido). */
export function MaioresMercado() {
  const { date } = useResumo()
  const q = useQuery({ queryKey: ['mercado-maiores', date], queryFn: () => fetchMercadoMaiores({ date: date ?? undefined }), staleTime: 10 * 60 * 1000, retry: false })
  if (q.isLoading) return <div className="h-40 bg-gray-50 rounded animate-pulse" />
  if (!q.data) return <p className="text-sm text-gray-500">O recorte dos maiores do mercado não está disponível neste snapshot.</p>
  const d = q.data
  const dados = [...d.unidades.map((u) => ({ name: u.nome, size: u.acessos, cor: u.grupo ? COR_GRUPO : COR_CNPJ, share: u.share })), { name: `Demais (${d.demais.unidades.toLocaleString('pt-BR')})`, size: d.demais.acessos, cor: COR_DEMAIS, share: d.demais.share }]
  return (
    <div className="space-y-6" data-testid="maiores-mercado">
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Posição das {d.operadoras.length} maiores operadoras, mês a mês</h2>
        <BumpChart meses={d.meses} series={d.operadoras.map((o) => ({ id: o.cnpj, nome: o.empresa, posicao: o.posicao }))} />
        <p className="text-xs text-gray-500">Posição por acessos declarados ao SICI (banda larga fixa), entre todos os CNPJs que declararam no mês; as operadoras mostradas são as maiores em {d.mes_referencia}. Linha interrompida = sem declaração no mês. É por CNPJ: um grupo econômico com vários CNPJs aparece dividido.</p>
        <details className="text-xs"><summary className="cursor-pointer text-primario-700">Ver dados (posição e acessos no último mês)</summary>
          <table className="mt-2 text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><th className="px-2 py-1 text-left">Operadora</th><th className="px-2 py-1 text-right">Posição em {d.mes_referencia}</th><th className="px-2 py-1 text-right">Posição há {d.meses.length - 1} meses</th><th className="px-2 py-1 text-right">Acessos</th></tr></thead>
            <tbody>{d.operadoras.map((o) => <tr key={o.cnpj} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/operadora/${o.cnpj}`} className="text-primario-700 hover:underline">{o.empresa}</Link></td><td className="px-2 py-1 text-right tabular-nums">{o.posicao[o.posicao.length - 1] ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{o.posicao[0] ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{(o.acessos[o.acessos.length - 1] ?? 0).toLocaleString('pt-BR')}</td></tr>)}</tbody></table></details>
      </section>
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">Maiores empresas ou grupos econômicos, por acessos declarados</h2>
        <div className="h-72 w-full" role="img" aria-label="Treemap das maiores empresas ou grupos pelos acessos declarados" data-testid="treemap">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap data={dados} dataKey="size" isAnimationActive={false} content={<Celula />} />
          </ResponsiveContainer>
        </div>
        <p className="text-xs text-gray-600"><span className="inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: COR_GRUPO }} /> grupo econômico (inferido do quadro societário, com mais de um CNPJ) · <span className="inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: COR_CNPJ }} /> CNPJ sem grupo · <span className="inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: COR_DEMAIS }} /> demais. Área proporcional aos acessos declarados; total de {d.total_acessos.toLocaleString('pt-BR')} acessos em {d.mes_referencia}.</p>
        <details className="text-xs"><summary className="cursor-pointer text-primario-700">Ver dados</summary>
          <table className="mt-2 text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><th className="px-2 py-1 text-left">Empresa ou grupo</th><th className="px-2 py-1 text-right">CNPJs com acessos</th><th className="px-2 py-1 text-right">Acessos</th><th className="px-2 py-1 text-right">Parcela</th></tr></thead>
            <tbody>{d.unidades.map((u) => <tr key={u.id} className="border-t border-gray-100"><td className="px-2 py-1">{u.grupo ? <Link to={`/grupo/${u.id}`} className="text-primario-700 hover:underline">{u.nome}</Link> : u.nome}{u.grupo && <span className="text-gray-400"> (grupo inferido)</span>}</td><td className="px-2 py-1 text-right tabular-nums">{u.cnpjs}</td><td className="px-2 py-1 text-right tabular-nums">{u.acessos.toLocaleString('pt-BR')}</td><td className="px-2 py-1 text-right tabular-nums">{pct(u.share)}</td></tr>)}</tbody></table></details>
      </section>
      <p className="text-xs text-gray-500">{d.aviso} Natureza: {d.natureza}. Snapshot {d.snapshot_date}.</p>
    </div>
  )
}
