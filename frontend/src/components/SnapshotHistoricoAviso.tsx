// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useLocation, useNavigate } from 'react-router-dom'
import { formatarReferencia } from './entidade/proveniencia'

/** `?date=` com cara de data de snapshot (AAAA-MM-DD); outra coisa não é tratada como histórico, a página lida com ela. */
export const DATA_DE_SNAPSHOT = /^\d{4}-\d{2}-\d{2}$/

/**
 * Link com a data de um snapshot anterior aos atuais, aberto sem login: explica o que é antes de qualquer modal (D3). Não é erro nem ausência de dado:
 * os snapshots são imutáveis e continuam guardados; só os dois mais recentes abrem sem login. Oferece entrar (preserva o endereço) ou ir para o atual.
 */
export function SnapshotHistoricoAviso({ data, atuais }: { data: string; atuais: string[] }) {
  const loc = useLocation()
  const navegar = useNavigate()
  const next = encodeURIComponent(loc.pathname + loc.search + loc.hash)
  function irParaOAtual() {
    const p = new URLSearchParams(loc.search)
    p.delete('date')
    const q = p.toString()
    navegar(`${loc.pathname}${q ? `?${q}` : ''}${loc.hash}`, { replace: true })
  }
  return (
    <div className="mx-auto my-12 max-w-xl rounded-xl border border-gray-200 bg-white p-8 text-center" role="status" data-testid="snapshot-historico">
      <h2 className="mb-2 text-base font-semibold text-gray-800">Snapshot histórico: {formatarReferencia(data)}</h2>
      <p className="mb-2 text-sm leading-relaxed text-gray-600">
        Você abriu um endereço que aponta para o snapshot de {formatarReferencia(data)}. Sem login, o site mostra os dois snapshots mais recentes
        ({atuais.map(formatarReferencia).join(' e ')}); os anteriores abrem com login e continuam guardados, sem alteração.
      </p>
      <p className="mb-5 text-sm leading-relaxed text-gray-600">Isto não é um erro: o link só deixa de abrir sem login quando saem snapshots mais novos.</p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <a href={`/login?next=${next}`} className="inline-block rounded-lg bg-[#0c1e45] px-5 py-2 text-sm text-white transition-colors hover:bg-primario-900">Entrar para ver este snapshot</a>
        <button type="button" onClick={irParaOAtual} className="rounded-lg border border-primario-300 px-5 py-2 text-sm text-primario-700 hover:bg-primario-50">Ir para o snapshot atual</button>
      </div>
    </div>
  )
}
