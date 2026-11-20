// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AccessError, fetchCaminho, queryColecao } from '../../services/api'
import { Provenance, type FonteEntrada } from '../../components/entidade'
import { useActiveDate } from '../../hooks/useSnapshot'
import { formatarCnpj, rotulosRepetidos } from '../../lib/marca'
import { formatarValor, linkDaLinha, type Cartao } from './cartoes'
import { useCartaoDerivado, type EstadoCartao } from './derivados'
import { ERRO_ORCAMENTO_ESGOTADO, useOrcamentoAvancado } from '../../auth/AuthContext'

interface Resposta { items?: Array<Record<string, unknown>>; total?: number }

/** Uma pergunta pronta respondida por uma consulta (`/query` ou rota): roda, mostra as primeiras linhas e o caminho para a lista completa. */
export function CartaoResposta({ cartao, fontes }: { cartao: Cartao; fontes?: FonteEntrada[] | null }) {
  const date = useActiveDate()
  const c = cartao.consulta
  const { pronto, esgotado } = useOrcamentoAvancado()
  const q = useQuery({
    queryKey: ['cartao', cartao.id, date],
    queryFn: (): Promise<Resposta> => (c.tipo === 'query'
      ? queryColecao<Resposta>(c.colecao, c.corpo, date ?? undefined)
      : c.tipo === 'get'
        ? fetchCaminho<Resposta>(c.caminho, { ...c.params, date: date ?? undefined })
        : Promise.reject(new Error('cartão derivado'))),
    enabled: !!date && c.tipo !== 'derivado' && pronto && !esgotado, staleTime: Infinity, gcTime: Infinity, retry: false,
  })
  const dados = q.data ? { items: q.data.items ?? [], total: q.data.total ?? (q.data.items ?? []).length } : undefined
  return <CartaoVisual cartao={cartao} fontes={fontes} estado={{ dados, carregando: q.isLoading, erro: esgotado ? ERRO_ORCAMENTO_ESGOTADO : q.error }} />
}

/** Cartão cuja resposta o navegador monta a partir de mais de uma fonte (distância até o PTT, cruzamento de coleções). */
export function CartaoDerivado({ cartao, fontes }: { cartao: Cartao; fontes?: FonteEntrada[] | null }) {
  return <CartaoVisual cartao={cartao} fontes={fontes} estado={useCartaoDerivado(cartao.id)} />
}

function CartaoVisual({ cartao, fontes, estado }: { cartao: Cartao; fontes?: FonteEntrada[] | null; estado: EstadoCartao }) {
  const date = useActiveDate()
  const itens = estado.dados?.items ?? []
  const total = estado.dados?.total
  const bloqueado = estado.erro instanceof AccessError
  const erro = !!estado.erro && !bloqueado
  return (
    <article className="bg-white rounded-lg border border-gray-200 p-4 flex flex-col" aria-labelledby={`cartao-${cartao.id}`}>
      <h2 id={`cartao-${cartao.id}`} className="text-base font-semibold text-gray-800">{cartao.titulo}</h2>
      <p className="text-sm text-gray-500 mt-0.5 mb-3">{cartao.pergunta}</p>
      <div className="flex-1 min-h-[7rem]">
        {estado.carregando && <p className="text-sm text-gray-400" role="status">Carregando…</p>}
        {bloqueado && <p className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" role="status">Esta resposta usa páginas avançadas e o tempo de uso sem login acabou. Entre para ver.</p>}
        {erro && <p className="text-sm text-gray-500" role="status">Não foi possível carregar esta resposta agora.</p>}
        {!!estado.dados && itens.length === 0 && <p className="text-sm text-gray-500" role="status">Nenhum resultado neste snapshot.</p>}
        {itens.length > 0 && (
          <ol className="divide-y divide-gray-50 text-sm">
            {itens.map((it, i) => {
              const repetidos = rotulosRepetidos(itens.map((x) => String(x[cartao.linha.rotulo] ?? '—')))
              const cnpj = typeof it.cnpj === 'string' ? it.cnpj : null
              return (
              <li key={i} className="py-1 flex items-baseline gap-2">
                <span className="text-xs text-gray-400 w-4 text-right">{i + 1}</span>
                <Link to={linkDaLinha(cartao.linha.link, it)} className="text-primario-600 hover:underline truncate flex-1">
                  {String(it[cartao.linha.rotulo] ?? '—')}
                  {cartao.linha.complemento && <span className="text-gray-400"> · {String(it[cartao.linha.complemento] ?? '')}</span>}
                  {cnpj && repetidos.has(String(it[cartao.linha.rotulo] ?? '—')) && <span className="text-gray-400 text-xs"> · CNPJ {formatarCnpj(cnpj)}</span>}
                </Link>
                <span className="tabular-nums text-gray-700">{formatarValor(it[cartao.linha.valor])}</span>
                <span className="text-xs text-gray-400">{cartao.linha.unidade}</span>
              </li>
              )
            })}
          </ol>
        )}
      </div>
      {typeof total === 'number' && total > itens.length && <p className="text-xs text-gray-400 mt-1">{total.toLocaleString('pt-BR')} no total</p>}
      <Link to={cartao.destino.to} className="mt-3 text-sm text-primario-600 hover:underline">{cartao.destino.rotulo} →</Link>
      <Provenance bloco={{ fontes: cartao.fontes }} fontes={fontes} snapshot={date} />
    </article>
  )
}
