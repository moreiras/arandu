// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useOrdenacao, type Acessor } from '../../lib/ordenacao'
import { ThOrdenavel } from './ThOrdenavel'

/**
 * "Ver dados (tabela)" (NBR 17225 5.2.4): a alternativa em texto de um gráfico, com os mesmos números,
 * recolhida por padrão. Monta a tabela a partir do array que alimenta o gráfico: uma coluna por campo simples (texto ou número);
 * `rotulos` dá nome legível aos campos e `campos` escolhe e ordena as colunas. Começa na ordem do gráfico; o cabeçalho ordena.
 */
export function VerDados({ dados, rotulos = {}, campos, titulo = 'Ver dados (tabela)' }: {
  dados: ReadonlyArray<Record<string, unknown>> | null | undefined
  rotulos?: Record<string, string>
  campos?: string[]
  titulo?: string
}) {
  const simples = (v: unknown) => typeof v === 'string' || typeof v === 'number' || v == null
  const chaves = !dados?.length ? [] : campos ?? Object.keys(dados[0]).filter((k) => !k.startsWith('_') && dados.some((d) => simples(d[k]) && d[k] != null))
  const acessores: Record<string, Acessor<Record<string, unknown>>> = {}
  for (const k of chaves) acessores[k] = (d) => { const v = d[k]; return typeof v === 'string' || typeof v === 'number' ? v : null }
  const { ordenados, props } = useOrdenacao(dados, acessores)
  if (!dados?.length) return null
  const fmt = (v: unknown) => (v == null ? '—' : typeof v === 'number' ? v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : String(v))
  return (
    <details className="mt-2 text-xs" data-testid="ver-dados">
      <summary className="cursor-pointer text-primario-700 hover:underline">{titulo}</summary>
      <div className="mt-1 max-h-80 overflow-auto rounded border border-gray-200">
        <table className="min-w-full" aria-label={titulo}>
          <thead className="sticky top-0 bg-gray-50 text-gray-600">
            <tr>{chaves.map((k) => <ThOrdenavel key={k} {...props(k)} className="px-2 py-1 text-left font-medium">{rotulos[k] ?? k}</ThOrdenavel>)}</tr>
          </thead>
          <tbody>
            {ordenados.map((d, i) => (
              <tr key={i} className="border-t border-gray-100">
                {chaves.map((k) => <td key={k} className={`px-2 py-0.5 ${typeof d[k] === 'number' ? 'text-right tabular-nums' : ''}`}>{fmt(d[k])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
