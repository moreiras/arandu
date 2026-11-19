// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { ProvenienciaCompacta } from '../ui/ProvenienciaCompacta'
import type { PedidoCitacao } from './CitarDado'
import type { FonteEntrada, ProvenienciaBloco } from './proveniencia'
import { ComoLer } from '../ui/ComoLer'

/**
 * Bloco de uma página de entidade: título, conteúdo e rodapé de proveniência (obrigatório: bloco sem fonte não existe).
 * - `semTitulo`: o conteúdo já traz seus próprios títulos (blocos migrados com colunas IPv6/IPv4 lado a lado); `titulo` vira o
 *   `aria-label` da região, sem h2 duplicado.
 * - `plana`: sem cartão (visual plano, só com o rodapé de proveniência).
 */
export function Section({ id, titulo, subtitulo, acoes, proveniencia, fontes, snapshot, semTitulo, plana, comoLer, recolhido, citacao, children }: {
  id?: string
  titulo: string
  subtitulo?: string
  acoes?: ReactNode
  proveniencia: ProvenienciaBloco
  fontes?: FonteEntrada[] | null
  snapshot?: string | null
  semTitulo?: boolean
  plana?: boolean
  /** "Como ler": o que o bloco mostra e o que não prova, num `<details>` sob o título. */
  comoLer?: string
  /** Bloco recolhível: o corpo fica dentro de um `<details>` fechado (o título, as ações e a proveniência seguem visíveis). */
  recolhido?: boolean
  /** "Citar este dado": a entidade e o bloco citados; sem ele o detalhe da proveniência não oferece a citação. */
  citacao?: PedidoCitacao
  children: ReactNode
}) {
  const tituloId = id ? `${id}-titulo` : undefined
  return (
    <section id={id} aria-labelledby={semTitulo ? undefined : tituloId} aria-label={semTitulo ? titulo : undefined}
      className={`scroll-mt-28 ${plana ? '' : 'bg-white rounded-lg border border-gray-200 p-4'}`}>
      {!semTitulo && (
        <div className="mb-3 flex flex-wrap items-baseline gap-2">
          <h2 id={tituloId} className="text-base font-semibold text-gray-800">{titulo}</h2>
          {subtitulo && <span className="text-xs font-normal text-gray-400">{subtitulo}</span>}
          {acoes && <div className="ml-auto">{acoes}</div>}
        </div>
      )}
      {comoLer && (
        <ComoLer className="mb-2"><p>{comoLer}</p></ComoLer>
      )}
      {recolhido
        ? <details data-testid="bloco-recolhido"><summary className="cursor-pointer select-none text-sm text-primario-700">Mostrar o conteúdo</summary><div className="mt-2">{children}</div></details>
        : children}
      <ProvenienciaCompacta bloco={proveniencia} fontes={fontes} snapshot={snapshot} citacao={citacao} />
    </section>
  )
}
