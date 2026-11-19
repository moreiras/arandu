// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import type { CeticEstimativa } from '../../../types/api'

const pct = (v?: number) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }))
const inteiro = (v?: number) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))

function Celula({ e }: { e?: CeticEstimativa }) {
  if (!e) return <td className="px-2 py-1 text-right">—</td>
  if (e.suprimido) return <td className="px-2 py-1 text-right text-gray-400" title={e.suprimido}>suprimido</td>
  return (
    <td className="px-2 py-1 text-right tabular-nums">
      {pct(e.proporcao)}%<span className="text-gray-400"> ±{pct(e.margem)}</span>
      {e.precisao === 'baixa' && <span className="text-aviso-700" title="Coeficiente de variação acima de 30%"> · precisão baixa</span>}
    </td>
  )
}

/**
 * Domicílios com Internet, computador e banda larga fixa na UF, ao lado da grande região e do Brasil. É estimativa do Arandurapé sobre os microdados
 * públicos da TIC Domicílios, com margem de erro de 95%: por UF a amostra é de 700 a 1.500 domicílios, então diferenças pequenas entre UFs não são conclusivas.
 */
export function CeticUfBloco({ dados }: BlocoProps<UfCtx>) {
  const c = dados.cetic
  if (!c) return null
  const linhas = [
    { rotulo: dados.uf, g: c.estimativas },
    ...(c.comparacao.regiao ? [{ rotulo: `Região ${c.comparacao.regiao.nome}`, g: c.comparacao.regiao }] : []),
    ...(c.comparacao.brasil ? [{ rotulo: 'Brasil', g: c.comparacao.brasil }] : []),
  ]
  const ids = Object.keys(c.indicadores)
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
              <th className="px-2 py-1">Recorte</th>
              {ids.map((i) => <th key={i} className="px-2 py-1 text-right font-medium" title={c.indicadores[i].definicao}>{c.indicadores[i].rotulo}</th>)}
              <th className="px-2 py-1 text-right">Entrevistados</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {linhas.map(({ rotulo, g }) => (
              <tr key={rotulo}>
                <td className="px-2 py-1 font-medium">{rotulo}</td>
                {ids.map((i) => <Celula key={i} e={g.indicadores[i]} />)}
                <td className="px-2 py-1 text-right tabular-nums text-gray-500">{inteiro(g.n)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">
        {c.aviso} Fonte: {c.fonte} · licença {c.licenca} · <a href="/uso-da-internet" className="text-primario-600 hover:underline">tabelas oficiais e estimativas de todas as UFs</a>.
      </p>
    </div>
  )
}
