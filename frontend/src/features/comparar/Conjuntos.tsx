// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Diagrama de Venn, gráfico UpSet e tabela de participantes (comparação entre 2 ou mais IXPs). */
import { Link } from 'react-router-dom'
import type { IXPCompareParticipant } from '../../types/api'
import { SET_COLORS } from './MetricasAfi'
import { nomeArquivo } from '../../lib/site'
import { asnEspecial } from '../../lib/asnEspecial'

/** Chave canônica de uma combinação: índices ordenados, separados por vírgula. */
export function comboKey(indices: number[]): string {
  return [...indices].sort((a, b) => a - b).join(',')
}

/** Todas as combinações não-vazias de 0..n-1. */
export function allCombos(n: number): number[][] {
  const out: number[][] = []
  for (let mask = 1; mask < (1 << n); mask++) {
    const combo: number[] = []
    for (let i = 0; i < n; i++) if (mask & (1 << i)) combo.push(i)
    out.push(combo)
  }
  return out
}

// ── Venn (≤3 conjuntos, não-interativo) ─────────────────────────────────────

export function VennDiagram({ labels, counts }: { labels: string[]; counts: Record<string, number> }) {
  const n = labels.length
  if (n === 2) {
    const w = 300, h = 200
    const r = 80
    const cA = { x: 110, y: 100 }
    const cB = { x: 190, y: 100 }
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-md mx-auto">
        <circle cx={cA.x} cy={cA.y} r={r} fill={SET_COLORS[0]} fillOpacity={0.35} stroke={SET_COLORS[0]} strokeWidth={1.5} />
        <circle cx={cB.x} cy={cB.y} r={r} fill={SET_COLORS[1]} fillOpacity={0.35} stroke={SET_COLORS[1]} strokeWidth={1.5} />
        <text x={70} y={100} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['0'] ?? 0}</text>
        <text x={230} y={100} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['1'] ?? 0}</text>
        <text x={150} y={100} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['0,1'] ?? 0}</text>
        <text x={cA.x} y={30} textAnchor="middle" className="text-xs fill-gray-600">{labels[0]}</text>
        <text x={cB.x} y={30} textAnchor="middle" className="text-xs fill-gray-600">{labels[1]}</text>
      </svg>
    )
  }
  // n === 3
  const w = 300, h = 260
  const r = 100
  const cA = { x: 110, y: 100 }
  const cB = { x: 190, y: 100 }
  const cC = { x: 150, y: 170 }
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-md mx-auto">
      <circle cx={cA.x} cy={cA.y} r={r} fill={SET_COLORS[0]} fillOpacity={0.28} stroke={SET_COLORS[0]} strokeWidth={1.5} />
      <circle cx={cB.x} cy={cB.y} r={r} fill={SET_COLORS[1]} fillOpacity={0.28} stroke={SET_COLORS[1]} strokeWidth={1.5} />
      <circle cx={cC.x} cy={cC.y} r={r} fill={SET_COLORS[2]} fillOpacity={0.28} stroke={SET_COLORS[2]} strokeWidth={1.5} />
      <text x={70}  y={70}  textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['0'] ?? 0}</text>
      <text x={230} y={70}  textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['1'] ?? 0}</text>
      <text x={150} y={235} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['2'] ?? 0}</text>
      <text x={150} y={65}  textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['0,1'] ?? 0}</text>
      <text x={95}  y={160} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['0,2'] ?? 0}</text>
      <text x={205} y={160} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['1,2'] ?? 0}</text>
      <text x={150} y={130} textAnchor="middle" className="text-sm font-semibold fill-gray-800">{counts['0,1,2'] ?? 0}</text>
      <text x={cA.x - 20} y={10} textAnchor="middle" className="text-xs fill-gray-600">{labels[0]}</text>
      <text x={cB.x + 20} y={10} textAnchor="middle" className="text-xs fill-gray-600">{labels[1]}</text>
      <text x={150} y={252} textAnchor="middle" className="text-xs fill-gray-600">{labels[2]}</text>
    </svg>
  )
}

// ── UpSet plot (2–4 conjuntos, interativo) ──────────────────────────────────

export function UpSetPlot({
  labels,
  counts,
  selected,
  onToggle,
}: {
  labels: string[]
  counts: { key: string; combo: number[]; count: number }[]
  selected: Set<string>
  onToggle: (key: string) => void
}) {
  const n = labels.length
  const maxCount = Math.max(1, ...counts.map(c => c.count))
  const barMaxH = 120
  const rowH = 22
  const colW = 34

  return (
    <div className="overflow-x-auto">
      <div style={{ display: 'inline-block', minWidth: '100%' }}>
        {/* Barras */}
        <div className="flex items-end gap-0.5 border-b border-gray-200 pb-1" style={{ height: barMaxH + 24 }}>
          {counts.map(c => {
            const h = Math.max(2, (c.count / maxCount) * barMaxH)
            const isSel = selected.has(c.key)
            return (
              <button
                key={c.key}
                type="button"
                onClick={() => onToggle(c.key)}
                className="flex flex-col items-center justify-end group"
                style={{ width: colW }}
                title={`${c.combo.map(i => labels[i]).join(' ∩ ')}: ${c.count} ASN(s) — clique para (des)selecionar`}
              >
                <span className={`text-xs mb-0.5 tabular-nums ${isSel ? 'font-bold text-primario-700' : 'text-gray-500'}`}>
                  {c.count}
                </span>
                <div
                  className={`w-4 rounded-t transition-colors ${isSel ? 'bg-primario-600' : 'bg-gray-300 group-hover:bg-gray-400'}`}
                  style={{ height: h }}
                />
              </button>
            )
          })}
        </div>
        {/* Matriz de pontos */}
        <div className="flex">
          <div className="flex flex-col justify-end pr-2" style={{ marginTop: 0 }}>
            {labels.map((l, i) => (
              <div key={i} className="flex items-center text-xs text-gray-600 justify-end" style={{ height: rowH }}>
                {l}
              </div>
            ))}
          </div>
          <div className="flex gap-0.5">
            {counts.map(c => {
              const isSel = selected.has(c.key)
              const includedIdx = c.combo
              const minI = Math.min(...includedIdx)
              const maxI = Math.max(...includedIdx)
              return (
                <button
                  key={c.key}
                  type="button"
                  onClick={() => onToggle(c.key)}
                  className="relative"
                  style={{ width: colW, height: rowH * n }}
                  title={`${c.combo.map(i => labels[i]).join(' ∩ ')}: ${c.count} ASN(s)`}
                >
                  {/* Linha conectando os pontos incluídos */}
                  {includedIdx.length > 1 && (
                    <div
                      className={isSel ? 'bg-primario-600' : 'bg-gray-400'}
                      style={{
                        position: 'absolute',
                        left: colW / 2 - 1,
                        top: minI * rowH + rowH / 2,
                        width: 2,
                        height: (maxI - minI) * rowH,
                      }}
                    />
                  )}
                  {Array.from({ length: n }, (_, i) => (
                    <div
                      key={i}
                      className={`absolute rounded-full ${
                        includedIdx.includes(i)
                          ? (isSel ? 'bg-primario-600' : 'bg-gray-500')
                          : 'bg-gray-200'
                      }`}
                      style={{
                        left: colW / 2 - 5,
                        top: i * rowH + rowH / 2 - 5,
                        width: 10,
                        height: 10,
                      }}
                    />
                  ))}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Tabela de participantes exportável em CSV ───────────────────────────────

/** O cadastro do IX.br traz ASNs sem página no snapshot (privados ou sem registro no RIR): sem link, com o motivo. */
function CelulaAsn({ p }: { p: IXPCompareParticipant }) {
  const especial = asnEspecial(p.asn)
  if (!especial && p.has_detail !== false) {
    return <Link to={`/asn/${p.asn}`} className="text-primario-600 hover:underline">AS{p.asn}</Link>
  }
  return (
    <span className="text-gray-600">
      AS{p.asn} <span className="font-sans text-gray-500">({especial ?? 'sem registro no snapshot'})</span>
    </span>
  )
}

export function ParticipantsTable({
  participants,
  labelByKey,
}: {
  participants: IXPCompareParticipant[]
  labelByKey: Record<string, string>
}) {
  function download() {
    const header = 'ASN,Nome,CNPJ,Blocos IPv6,Blocos IPv4,IXPs'
    const lines = participants.map(r => {
      const name = (r.name ?? '').replace(/"/g, '""')
      const cnpj = r.cnpj ?? ''
      const v4 = r.ipv4_prefixes.join(' ')
      const v6 = r.ipv6_prefixes.join(' ')
      const ixpNames = r.member_of.map(k => labelByKey[k] ?? k).join(' ')
      return `${r.asn},"${name}",${cnpj},"${v6}","${v4}","${ixpNames}"`
    })
    const csv = [header, ...lines].join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = nomeArquivo('comparar-ixps.csv')
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700">Participantes ({participants.length})</h3>
        <button
          type="button"
          onClick={download}
          disabled={participants.length === 0}
          className="text-xs px-3 py-1.5 rounded border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Exportar CSV
        </button>
      </div>
      <div className="max-h-96 overflow-y-auto rounded border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 text-gray-500 uppercase sticky top-0">
            <tr>
              <th className="px-2 py-1.5 text-left font-medium">ASN</th>
              <th className="px-2 py-1.5 text-left font-medium">Nome</th>
              <th className="px-2 py-1.5 text-left font-medium">CNPJ</th>
              <th className="px-2 py-1.5 text-left font-medium">Blocos IPv6</th>
              <th className="px-2 py-1.5 text-left font-medium">Blocos IPv4</th>
              <th className="px-2 py-1.5 text-left font-medium">IXPs</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {participants.length === 0 && (
              <tr><td colSpan={6} className="px-2 py-6 text-center text-gray-400">Nenhum participante nesta seleção</td></tr>
            )}
            {participants.map(p => (
              <tr key={p.asn} className="hover:bg-gray-50">
                <td className="px-2 py-1.5 font-mono">
                  <CelulaAsn p={p} />
                </td>
                <td className="px-2 py-1.5 max-w-[220px] truncate" title={p.name ?? ''}>{p.name || '—'}</td>
                <td className="px-2 py-1.5 font-mono">{p.cnpj ?? '—'}</td>
                <td className="px-2 py-1.5 max-w-[200px] truncate" title={p.ipv6_prefixes.join(' ')}>
                  {p.ipv6_prefixes.length ? p.ipv6_prefixes.join(', ') : '—'}
                </td>
                <td className="px-2 py-1.5 max-w-[200px] truncate" title={p.ipv4_prefixes.join(' ')}>
                  {p.ipv4_prefixes.length ? p.ipv4_prefixes.join(', ') : '—'}
                </td>
                <td className="px-2 py-1.5">
                  {p.member_of.map(k => labelByKey[k] ?? k).join(', ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
