// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState, type ReactNode } from 'react'
import { ProvenienciaCompacta } from './ProvenienciaCompacta'
import type { FonteEntrada, ProvenienciaBloco } from '../entidade/proveniencia'
import { ComoLer } from './ComoLer'

/**
 * Bloco de página: título (h2) sempre visível, botão de recolher, ações, "Como ler" recolhível (o texto das ressalvas, idêntico,
 * sai do corpo e vai para cá) e proveniência compacta. Bloco sem fonte não existe, como no `Section`.
 */
export function Bloco({ id, titulo, subtitulo, acoes, recolhivel = true, recolhido = false, comoLer, proveniencia, fontes, snapshot, children }: {
  id?: string
  titulo: string
  subtitulo?: string
  acoes?: ReactNode
  recolhivel?: boolean
  /** Estado inicial. */
  recolhido?: boolean
  comoLer?: ReactNode
  proveniencia: ProvenienciaBloco
  fontes?: FonteEntrada[] | null
  snapshot?: string | null
  children: ReactNode
}) {
  const [fechado, setFechado] = useState(recolhido)
  const tid = id ? `${id}-titulo` : undefined
  const cid = id ? `${id}-conteudo` : undefined
  return (
    <section id={id} aria-labelledby={tid} className="scroll-mt-28 rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 id={tid} className="text-titulo-3 text-gray-800">
          {recolhivel ? (
            <button type="button" className="inline-flex items-center gap-1 text-left" aria-expanded={!fechado} aria-controls={cid} onClick={() => setFechado((v) => !v)}>
              <span aria-hidden="true" className="text-gray-400">{fechado ? '▸' : '▾'}</span>{titulo}
            </button>
          ) : titulo}
        </h2>
        {subtitulo && <span className="text-xs text-gray-500">{subtitulo}</span>}
        {acoes && <div className="ml-auto">{acoes}</div>}
      </div>
      <div id={cid} hidden={fechado} className="mt-3">
        {children}
        {comoLer && (
          <ComoLer className="mt-3">{comoLer}</ComoLer>
        )}
      </div>
      <ProvenienciaCompacta bloco={proveniencia} fontes={fontes} snapshot={snapshot} />
    </section>
  )
}
