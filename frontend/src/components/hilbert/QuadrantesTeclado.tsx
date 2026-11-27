// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Botões de quadrante sobre o mapa: um por quadrante com dado, na ordem de leitura (linha a linha), focáveis pelo Tab e acionados por
 * Enter ou Espaço (o comportamento nativo do botão). Ficam transparentes e sem captura do mouse (o clique no mapa continua no canvas,
 * o hover não passa por aqui); só o anel de foco aparece. O foco volta ao botão ao fechar o zoom pelo `ModalAcessivel`, que guarda
 * o elemento focado ao abrir.
 */
export interface QuadranteBotao {
  /** Coluna e linha do quadrante na grade de quadrantes. */
  col: number
  lin: number
  /** Nome acessível, p.ex. "Ampliar quadrante 2001::/20" (ver `nomeAmpliar`). */
  nome: string
  aoAbrir: () => void
}

export function QuadrantesTeclado({ lado, quadrantes }: { lado: number; quadrantes: QuadranteBotao[] }) {
  const ordenados = [...quadrantes].sort((a, b) => a.lin - b.lin || a.col - b.col)
  const pct = 100 / lado
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {ordenados.map((q) => (
        <button
          key={`${q.col},${q.lin}`}
          type="button"
          data-quadrante=""
          aria-label={q.nome}
          onClick={q.aoAbrir}
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
