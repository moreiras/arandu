// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { avisoLinkCitacao, linkPermanente, montarCitacao, type ValorCitado } from './citacao'
import type { FonteEntrada } from './proveniencia'
import { useAppStore } from '../../store/app'

export interface PedidoCitacao { entidade: string; bloco: string; blocoId?: string; valor?: string; valores?: ValorCitado[] }

/** Os indicadores (`Kpi`) que o bloco mostra agora, como rótulo e valor da tela: é o que a citação carrega para valer sozinha. */
export function valoresDoBloco(origem: Element | null): ValorCitado[] {
  const secao = origem?.closest('section')
  if (!secao) return []
  return Array.from(secao.querySelectorAll('[data-testid="kpi"]')).map((k) => ({
    rotulo: k.getAttribute('data-kpi-rotulo') ?? '',
    valor: (k.querySelector('[data-kpi-valor]')?.textContent ?? '').trim(),
  })).filter((v) => v.rotulo && v.valor && v.valor !== '—')
}

/**
 * "Citar este dado": texto pronto para copiar, com entidade, os valores do bloco, fonte e referência, snapshot e link permanente; mora no detalhe da
 * proveniência de cada bloco. O link só abre sem login enquanto o snapshot é um dos dois mais recentes, e o aviso diz isso: por isso o texto leva os
 * valores e as fontes com as datas, e vale mesmo depois que o link passar a exigir login (D3).
 */
export function CitarDado({ pedido, fontes, fontesEntradas, snapshot, recentes }: { pedido: PedidoCitacao; fontes: string[]; fontesEntradas?: FonteEntrada[] | null; snapshot?: string | null; recentes?: string[] | null }) {
  const loc = useLocation()
  const raiz = useRef<HTMLDivElement>(null)
  const [copiado, setCopiado] = useState(false)
  const [lidos, setLidos] = useState<ValorCitado[]>([])
  const atuais = useAppStore((s) => s.snapshotsAtuais)
  // Os valores são lidos da tela quando o detalhe abre (os blocos carregam dados depois da primeira renderização).
  useEffect(() => {
    if (pedido.valores) return
    const detalhe = raiz.current?.closest('details')
    const ler = () => setLidos(valoresDoBloco(raiz.current))
    ler()
    detalhe?.addEventListener('toggle', ler)
    return () => detalhe?.removeEventListener('toggle', ler)
  }, [pedido.valores])
  const texto = montarCitacao({ ...pedido, valores: pedido.valores ?? lidos, fontes, fontesEntradas, snapshot, acessoEm: new Date(), url: linkPermanente(window.location.origin, loc.pathname, loc.search, snapshot, pedido.blocoId) })
  async function copiar() {
    try { await navigator.clipboard.writeText(texto); setCopiado(true); setTimeout(() => setCopiado(false), 2000) } catch { setCopiado(false) }
  }
  return (
    <div ref={raiz} className="mt-2 border-t border-gray-100 pt-2" data-testid="citar-dado">
      <p className="mb-1 font-medium text-gray-700">Citar este dado</p>
      <textarea readOnly value={texto} rows={6} aria-label="Texto de citação" onFocus={(e) => e.currentTarget.select()} className="w-full rounded border border-gray-200 bg-gray-50 p-1.5 text-xs text-gray-700" />
      <p className="mt-1 text-xs text-gray-500" data-testid="aviso-link-citacao">{avisoLinkCitacao(snapshot, recentes ?? atuais)}</p>
      <button type="button" onClick={copiar} className="mt-1 rounded border border-primario-300 px-2 py-0.5 text-xs text-primario-700 hover:bg-primario-50">{copiado ? 'Copiado' : 'Copiar citação'}</button>
    </div>
  )
}
