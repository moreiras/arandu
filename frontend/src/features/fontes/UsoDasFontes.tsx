// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { palavra } from '../../lib/sintese'
import { abasDe, todosOsBlocos } from '../entidade/registry'
import type { FonteCatalogo } from './catalogo'
import { indiceFontePaginas, porPagina } from './usoFontes'

/** O registro de blocos se preenche quando o módulo de cada entidade é importado; o índice os carrega sob demanda, num pedaço à parte do código. */
async function carregarRegistro() {
  await Promise.all([import('../asn'), import('../ptt'), import('../operadora'), import('../grupo'), import('../uf'), import('../municipio'), import('../prefixo')])
  return todosOsBlocos()
}

/**
 * Índice "fonte → páginas" (FONT 5.5): para cada fonte do catálogo, em quais blocos de página de entidade ela é declarada. Derivado do registro de
 * blocos (`BlocoDef.fontes`), sem lista à mão. Recolhido; o registro só é carregado ao abrir.
 */
export function UsoDasFontes({ fontes }: { fontes: FonteCatalogo[] }) {
  const [aberto, setAberto] = useState(false)
  const registro = useQuery({ queryKey: ['registro-de-blocos'], queryFn: carregarRegistro, enabled: aberto, staleTime: Infinity, gcTime: Infinity, retry: false })
  const indice = registro.data ? indiceFontePaginas(registro.data, fontes.map((f) => f.id), abasDe) : null
  const sem = indice ? fontes.filter((f) => (indice.get(f.id) ?? []).length === 0) : []
  return (
    <details className="rounded-lg border border-gray-200 bg-white px-4 py-2" data-testid="uso-das-fontes" onToggle={(e) => setAberto((e.currentTarget as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer"><h2 className="inline text-base font-semibold text-gray-800">Onde cada fonte aparece</h2></summary>
      <div className="mt-2 space-y-3 text-sm">
        <p className="text-xs text-gray-600">
          Para cada fonte, os blocos das páginas de AS, PTT, operadora, grupo econômico, UF, município e prefixo que a declaram. Cada bloco combina várias fontes:
          constar aqui não significa que o número vem só dela. O índice é montado a partir da declaração de fontes de cada bloco, não de uma lista à mão.
        </p>
        {aberto && registro.isLoading && <p className="text-xs text-gray-500" role="status">Montando o índice…</p>}
        {registro.isError && <p className="text-xs text-aviso-700" role="status">Não foi possível montar o índice agora.</p>}
        {indice && (
          <>
            <ul className="divide-y divide-gray-100" aria-label="Fontes e as páginas em que aparecem">
              {fontes.filter((f) => (indice.get(f.id) ?? []).length > 0).map((f) => {
                const usos = indice.get(f.id) ?? []
                return (
                  <li key={f.id} className="py-2" data-testid="uso-fonte" data-fonte={f.id}>
                    <div className="font-medium text-gray-900">{f.nome} <span className="text-xs font-mono text-gray-400">{f.id}</span></div>
                    <p className="text-xs text-gray-500">{usos.length} {palavra(usos.length, 'bloco', 'blocos')} em {porPagina(usos).length} {palavra(porPagina(usos).length, 'página', 'páginas')}</p>
                    <ul className="mt-1 space-y-0.5 text-xs text-gray-700">
                      {porPagina(usos).map((g) => (
                        <li key={g.pagina}><span className="text-gray-500">{g.pagina}: </span>{g.blocos.map((b) => (b.aba ? `${b.titulo} (aba ${b.aba})` : b.titulo)).join('; ')}</li>
                      ))}
                    </ul>
                  </li>
                )
              })}
            </ul>
            {sem.length > 0 && (
              <p className="text-xs text-gray-600" data-testid="fontes-sem-bloco">
                {sem.length} {palavra(sem.length, 'fonte não é declarada', 'fontes não são declaradas')} por bloco de página de entidade ({sem.map((f) => f.nome).join('; ')}).
                Podem alimentar páginas de painel (Panorama, Home e listas), a API e o MCP, que este índice não cobre.
              </p>
            )}
          </>
        )}
      </div>
    </details>
  )
}
