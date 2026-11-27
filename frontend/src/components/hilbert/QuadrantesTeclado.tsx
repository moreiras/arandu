// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useRef, useState, type KeyboardEvent } from 'react'

/**
 * Botões de quadrante sobre o mapa, como um grupo de uma única parada de Tab (roving tabindex): só o quadrante ativo tem tabIndex 0.
 * Setas movem para o quadrante com dado mais próximo naquela direção da grade, Home e End vão ao primeiro e ao último (ordem de leitura),
 * Enter e Espaço abrem o zoom (comportamento nativo do botão). Os botões são transparentes e sem captura do mouse (clique e hover seguem
 * no canvas); só o anel de foco aparece. Ao fechar o zoom o `ModalAcessivel` devolve o foco ao botão que o abriu, que é o ativo.
 */
export interface QuadranteBotao {
  /** Coluna e linha do quadrante na grade de quadrantes. */
  col: number
  lin: number
  /** Nome acessível, p.ex. "Ampliar quadrante 2001::/20" (ver `nomeAmpliar`). */
  nome: string
  aoAbrir: () => void
}

const chave = (q: { col: number; lin: number }) => `${q.col},${q.lin}`

/**
 * Quadrante vizinho na direção (dc, dl): entre os que estão do lado certo, o de menor distância, com a distância transversal
 * pesando o dobro, de modo que o da mesma linha ou coluna vence. Sem candidato, devolve null.
 */
export function vizinho(atual: QuadranteBotao, todos: QuadranteBotao[], dc: number, dl: number): QuadranteBotao | null {
  let melhor: QuadranteBotao | null = null
  let custo = Infinity
  for (const q of todos) {
    const ac = (q.col - atual.col) * dc + (q.lin - atual.lin) * dl
    if (ac <= 0) continue
    const tr = dc !== 0 ? q.lin - atual.lin : q.col - atual.col
    const c = ac * ac + 4 * tr * tr
    if (c < custo) { custo = c; melhor = q }
  }
  return melhor
}

export function QuadrantesTeclado({ lado, quadrantes, rotulo }: { lado: number; quadrantes: QuadranteBotao[]; rotulo: string }) {
  const ordenados = [...quadrantes].sort((a, b) => a.lin - b.lin || a.col - b.col)
  const [ativo, setAtivo] = useState<string | null>(null)
  const botoes = useRef(new Map<string, HTMLButtonElement>())
  const pct = 100 / lado
  const chaveAtiva = ordenados.some((q) => chave(q) === ativo) ? ativo : ordenados[0] ? chave(ordenados[0]) : null

  const ir = (q: QuadranteBotao | null | undefined) => {
    if (!q) return
    setAtivo(chave(q))
    botoes.current.get(chave(q))?.focus()
  }
  const tecla = (e: KeyboardEvent<HTMLButtonElement>, q: QuadranteBotao) => {
    const dir: Record<string, [number, number]> = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] }
    if (e.key in dir) { e.preventDefault(); ir(vizinho(q, ordenados, dir[e.key][0], dir[e.key][1])) }
    else if (e.key === 'Home') { e.preventDefault(); ir(ordenados[0]) }
    else if (e.key === 'End') { e.preventDefault(); ir(ordenados[ordenados.length - 1]) }
  }

  return (
    <div role="group" aria-label={rotulo} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {ordenados.map((q) => (
        <button
          key={chave(q)}
          ref={(el) => { if (el) botoes.current.set(chave(q), el); else botoes.current.delete(chave(q)) }}
          type="button"
          data-quadrante=""
          aria-label={q.nome}
          tabIndex={chave(q) === chaveAtiva ? 0 : -1}
          onFocus={() => setAtivo(chave(q))}
          onKeyDown={(e) => tecla(e, q)}
          onClick={() => { setAtivo(chave(q)); q.aoAbrir() }}
          className="focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primario-700"
          style={{
            position: 'absolute', left: `${q.col * pct}%`, top: `${q.lin * pct}%`, width: `${pct}%`, height: `${pct}%`,
            background: 'transparent', border: 0, padding: 0, margin: 0, pointerEvents: 'none',
          }}
        />
      ))}
    </div>
  )
}
