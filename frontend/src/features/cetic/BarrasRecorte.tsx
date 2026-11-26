// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { CeticLinha } from '../../types/api'
import { TEXTO_ZERO_REGISTRADO, estadoMargem } from './margem'

export interface Recorte { dimensao: string; recorte: string; valor: number | null; margem: number | null }

/** Os recortes de uma coluna (item × resposta) da tabela, na ordem da planilha, com o valor e a margem de erro da medida escolhida. */
export function recortesDaColuna(linhas: CeticLinha[], coluna: string, medida: 'proporcao' | 'total'): Recorte[] {
  const vistos = new Set<string>()
  const out: Recorte[] = []
  for (const l of linhas) {
    const col = l.item ? `${l.item}: ${l.resposta}` : l.resposta
    const chave = `${l.dimensao}|${l.recorte}`
    if (col !== coluna || vistos.has(chave)) continue
    vistos.add(chave)
    out.push({ dimensao: l.dimensao, recorte: l.recorte, valor: medida === 'proporcao' ? l.proporcao : l.total, margem: medida === 'proporcao' ? l.margem_proporcao : l.margem_total })
  }
  return out
}

const fmt = (v: number, medida: 'proporcao' | 'total') => (medida === 'proporcao' ? `${v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%` : Math.round(v).toLocaleString('pt-BR'))

/**
 * Barras por recorte: uma barra por categoria, agrupadas pela dimensão (Total, região, área, sexo, classe…), com a margem de erro como traço sobre a barra. Ordem da planilha,
 * não do maior valor: a pesquisa é amostral e a diferença entre duas barras só é diferença quando as margens não se sobrepõem, o que o gráfico deixa ver sem declarar.
 */
export function BarrasRecorte({ recortes, medida, coluna }: { recortes: Recorte[]; medida: 'proporcao' | 'total'; coluna: string }) {
  const comValor = recortes.filter((r) => r.valor != null)
  if (comValor.length === 0) return <p className="text-sm text-gray-500">Esta coluna não tem valor publicado nos recortes.</p>
  const maximo = medida === 'proporcao' ? 100 : Math.max(...comValor.map((r) => (r.valor ?? 0) + (r.margem ?? 0))) * 1.05
  const largura = (v: number) => `${Math.min(100, Math.max(0, (v / maximo) * 100))}%`
  const dimensoes = [...new Set(recortes.map((r) => r.dimensao))]
  return (
    <figure className="space-y-3" data-testid="barras-recorte" aria-label={`${coluna}, por recorte`}>
      {dimensoes.map((d) => (
        <div key={d}>
          {d !== 'Total' && <h3 className="mb-1 text-xs font-semibold text-gray-600">{d}</h3>}
          <ul className="space-y-1">
            {recortes.filter((r) => r.dimensao === d).map((r) => {
              const estado = estadoMargem(r.valor, r.margem, medida)
              const m = estado === 'zero_registrado' ? null : r.margem
              const nota = estado === 'zero_registrado' ? `, ${TEXTO_ZERO_REGISTRADO}` : estado === 'precisao_baixa' ? ', precisão baixa' : ''
              return (
                <li key={`${d}|${r.recorte}`} className="grid grid-cols-[1fr_auto] items-center gap-x-2 gap-y-0.5 text-xs sm:grid-cols-[minmax(6rem,11rem)_1fr_9rem]">
                  <span className="order-1 truncate text-gray-700" title={r.recorte}>{r.recorte}</span>
                  <span role="img" aria-label={r.valor == null ? `${r.recorte}: sem valor` : `${r.recorte}: ${fmt(r.valor, medida)}${m != null ? `, margem de ${fmt(m, medida)}` : ''}${nota}`} className="relative order-3 col-span-2 block h-4 rounded-sm bg-gray-100 sm:order-2 sm:col-span-1">
                    {r.valor != null && <span className="absolute inset-y-0.5 left-0 rounded-sm bg-slate-600" style={{ width: largura(r.valor) }} aria-hidden="true" />}
                    {r.valor != null && m != null && <span className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-gray-900" style={{ left: largura(Math.max(0, r.valor - m)), width: `calc(${largura(Math.min(maximo, r.valor + m))} - ${largura(Math.max(0, r.valor - m))})` }} aria-hidden="true" />}
                  </span>
                  <span className="order-2 text-right tabular-nums text-gray-700 sm:order-3">{r.valor == null ? '—' : fmt(r.valor, medida)}{r.valor != null && m != null && <span className="text-gray-500"> ±{fmt(m, medida)}</span>}
                    {estado === 'zero_registrado' && <span className="text-gray-500" title={TEXTO_ZERO_REGISTRADO}> ±{'—'}<span className="sr-only"> ({TEXTO_ZERO_REGISTRADO})</span></span>}
                    {estado === 'precisao_baixa' && <span className="text-aviso-900"> · precisão baixa</span>}</span>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
      <figcaption className="text-xs text-gray-500">Barra = valor estimado; traço preto = margem de erro. Pesquisa amostral: se as margens de duas barras se sobrepõem, a diferença pode ser acaso. "±{'—'}": {TEXTO_ZERO_REGISTRADO}; "precisão baixa": margem de pelo menos metade do valor. Ordem da planilha, sem ranking.</figcaption>
    </figure>
  )
}
