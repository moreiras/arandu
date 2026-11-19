// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { linkPermanente, montarCitacao } from './citacao'
import type { FonteEntrada } from './proveniencia'

export interface PedidoCitacao { entidade: string; bloco: string; blocoId?: string; valor?: string }

/** "Citar este dado": texto pronto para copiar, com entidade, fonte, referência, snapshot e link permanente; mora no detalhe da proveniência de cada bloco. */
export function CitarDado({ pedido, fontes, fontesEntradas, snapshot }: { pedido: PedidoCitacao; fontes: string[]; fontesEntradas?: FonteEntrada[] | null; snapshot?: string | null }) {
  const loc = useLocation()
  const [copiado, setCopiado] = useState(false)
  const texto = montarCitacao({ ...pedido, fontes, fontesEntradas, snapshot, acessoEm: new Date(), url: linkPermanente(window.location.origin, loc.pathname, loc.search, snapshot, pedido.blocoId) })
  async function copiar() {
    try { await navigator.clipboard.writeText(texto); setCopiado(true); setTimeout(() => setCopiado(false), 2000) } catch { setCopiado(false) }
  }
  return (
    <div className="mt-2 border-t border-gray-100 pt-2" data-testid="citar-dado">
      <p className="mb-1 font-medium text-gray-700">Citar este dado</p>
      <textarea readOnly value={texto} rows={4} aria-label="Texto de citação" onFocus={(e) => e.currentTarget.select()} className="w-full rounded border border-gray-200 bg-gray-50 p-1.5 text-xs text-gray-700" />
      <button type="button" onClick={copiar} className="mt-1 rounded border border-primario-300 px-2 py-0.5 text-xs text-primario-700 hover:bg-primario-50">{copiado ? 'Copiado' : 'Copiar citação'}</button>
    </div>
  )
}
