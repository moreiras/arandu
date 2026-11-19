// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { CATEGORIAS_SEGURAS } from '../../lib/escalasMapa'

export interface SerieBump { id: string; nome: string; posicao: (number | null)[] }

const L = 720, ALT_LINHA = 26, MARGEM = { e: 28, d: 150, t: 22, b: 24 }

/**
 * Largura mínima de 720 px (o texto fica em 12 px): no celular o gráfico rola dentro da própria caixa e a página não rola.
 * Bump chart: a posição de cada operadora, mês a mês (1 = a que mais declarou acessos). O eixo vai da posição 1 à pior posição vista; linha
 * interrompida onde a operadora não declarou no mês. Rótulo direto no fim da linha (sem legenda), cores seguras para daltonismo. Não diz "melhor" nem "pior".
 */
export function BumpChart({ meses, series }: { meses: string[]; series: SerieBump[] }) {
  const pior = Math.max(1, ...series.flatMap((s) => s.posicao.filter((p): p is number => p != null)))
  const H = MARGEM.t + MARGEM.b + (pior - 1) * ALT_LINHA + 8
  const x = (i: number) => MARGEM.e + (meses.length <= 1 ? 0 : (i / (meses.length - 1)) * (L - MARGEM.e - MARGEM.d))
  const y = (p: number) => MARGEM.t + (p - 1) * ALT_LINHA
  const marcas = meses.map((m, i) => [i, m] as const).filter(([i]) => i === 0 || i === meses.length - 1 || i % 6 === 0)
  return (
    <div className="overflow-x-auto"><svg viewBox={`0 0 ${L} ${H}`} className="w-full min-w-[720px] max-w-[900px] h-auto" role="img" aria-label={`Posição mês a mês das ${series.length} maiores operadoras, de ${meses[0]} a ${meses[meses.length - 1]}`} data-testid="bump">
      {Array.from({ length: pior }, (_, i) => i + 1).map((p) => (
        <g key={p}><line x1={MARGEM.e} x2={L - MARGEM.d} y1={y(p)} y2={y(p)} stroke="#e5e7eb" strokeWidth="1" /><text x={MARGEM.e - 8} y={y(p) + 4} textAnchor="end" fontSize="12" fill="#6b7280">{p}</text></g>
      ))}
      {marcas.map(([i, m]) => <text key={m} x={x(i)} y={H - 6} textAnchor={i === 0 ? 'start' : i === meses.length - 1 ? 'end' : 'middle'} fontSize="12" fill="#6b7280">{m}</text>)}
      {series.map((s, k) => {
        const cor = CATEGORIAS_SEGURAS[k % CATEGORIAS_SEGURAS.length]
        // trechos contínuos (sem posição no mês = quebra)
        const trechos: [number, number][][] = []
        s.posicao.forEach((p, i) => { if (p == null) return; const t = trechos[trechos.length - 1]; if (t && t[t.length - 1][0] === i - 1) t.push([i, p]); else trechos.push([[i, p]]) })
        const ultimo = [...s.posicao].map((p, i) => [i, p] as const).filter(([, p]) => p != null).pop()
        return (
          <g key={s.id}>
            {trechos.map((t, j) => t.length > 1 && <polyline key={j} points={t.map(([i, p]) => `${x(i)},${y(p)}`).join(' ')} fill="none" stroke={cor} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />)}
            {trechos.flat().map(([i, p]) => <circle key={i} cx={x(i)} cy={y(p)} r={i === (ultimo?.[0] ?? -1) ? 4 : 2} fill={cor} />)}
            {ultimo && ultimo[1] != null && <text x={x(ultimo[0]) + 9} y={y(ultimo[1]) + 4} fontSize="12" fill="#1f2937">{s.nome.length > 20 ? s.nome.slice(0, 19) + '…' : s.nome}</text>}
          </g>
        )
      })}
    </svg></div>
  )
}
