// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Mínimo de blocos para valer um sumário: abaixo disso a página cabe em uma tela e o índice só ocupa espaço. */
const MINIMO = 4

/**
 * Sumário de âncoras no topo das páginas de entidade: os blocos já tinham `id="bloco-…"` e nada apontava para eles.
 * Navegação por âncora comum (sem estado do React): no celular vira uma faixa que rola dentro do próprio contêiner.
 */
export function SumarioBlocos({ itens }: { itens: { id: string; titulo: string }[] }) {
  if (itens.length < MINIMO) return null
  return (
    <nav aria-label="Nesta página" className="text-xs">
      <ul className="flex gap-1.5 overflow-x-auto sm:flex-wrap sm:overflow-visible pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {itens.map((i) => (
          <li key={i.id} className="flex-shrink-0">
            <a href={`#${i.id}`} className="block rounded-full border border-gray-200 bg-white px-2.5 py-1 text-gray-600 hover:border-primario-300 hover:text-primario-700 whitespace-nowrap">
              {i.titulo}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
