// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { QualIndicador } from '../../types/api'

export interface LinhaBullet { prestadora: string; valor: number | null }

/** "90%" → 90; "1,5" → 1.5; `null` se a referência não é um número simples (igual ao `_num` do servidor). */
export function numeroDaReferencia(ref: string | null | undefined): number | null {
  if (!ref) return null
  const n = Number(String(ref).replace('%', '').replace(/\s/g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

const fmt = (n: number) => n.toLocaleString('pt-BR', { maximumFractionDigits: 2 })

/**
 * Bullet chart do indicador por prestadora: a barra é o valor nacional da prestadora; o fundo marca as duas referências da Anatel
 * (traços verticais). Cores neutras e ordem alfabética: o sentido de "melhor" depende do indicador e o gráfico não ranqueia nem julga.
 * Sem referência numérica, só a barra, na escala do maior valor.
 */
export function BulletPrestadoras({ linhas, indicador }: { linhas: LinhaBullet[]; indicador: QualIndicador }) {
  const sup = numeroDaReferencia(indicador.referencia_superior)
  const inf = numeroDaReferencia(indicador.referencia_inferior)
  const valores = linhas.map((l) => l.valor).filter((v): v is number => v != null)
  if (valores.length === 0) return null
  const porcentagem = indicador.unidade.includes('%')
  const topo = Math.max(...valores, sup ?? 0, inf ?? 0) * 1.08 || 1
  const escala = porcentagem ? Math.max(100, topo) : topo
  const pos = (v: number) => `${Math.min(100, Math.max(0, (v / escala) * 100))}%`
  const refs = [inf != null ? { v: inf, r: 'inferior' } : null, sup != null ? { v: sup, r: 'superior' } : null].filter((x): x is { v: number; r: string } => !!x)
  return (
    <figure className="space-y-1" data-testid="bullet-prestadoras" aria-label={`${indicador.codigo} por prestadora, com as referências da Anatel`}>
      <ul className="space-y-1">
        {linhas.map((l) => (
          <li key={l.prestadora} className="grid grid-cols-[minmax(6rem,10rem)_1fr_4.5rem] items-center gap-2 text-xs">
            <span className="truncate text-gray-700" title={l.prestadora}>{l.prestadora}</span>
            <span role="img" aria-label={l.valor == null ? `${l.prestadora}: sem valor` : `${l.prestadora}: ${fmt(l.valor)} ${indicador.unidade}`} className="relative block h-4 rounded-sm bg-gray-100">
              {inf != null && sup != null && <span className="absolute inset-y-0 bg-gray-200" style={{ left: pos(Math.min(inf, sup)), width: `calc(${pos(Math.max(inf, sup))} - ${pos(Math.min(inf, sup))})` }} aria-hidden="true" />}
              {l.valor != null && <span className="absolute inset-y-1 left-0 rounded-sm bg-slate-600" style={{ width: pos(l.valor) }} aria-hidden="true" />}
              {refs.map((x) => <span key={x.r} className="absolute inset-y-0 w-0.5 bg-gray-900" style={{ left: pos(x.v) }} aria-hidden="true" />)}
            </span>
            <span className="text-right tabular-nums text-gray-700">{l.valor == null ? '—' : fmt(l.valor)}</span>
          </li>
        ))}
      </ul>
      <figcaption className="text-xs text-gray-500">
        Barra = valor nacional da prestadora ({indicador.unidade}). Traços pretos = referências da Anatel{refs.length ? ': ' + refs.map((x) => `${x.r} ${fmt(x.v)}`).join(', ') : ' (este indicador não tem referência numérica)'}; a faixa cinza é o intervalo entre elas. Ordem alfabética, sem ranking.
      </figcaption>
    </figure>
  )
}
