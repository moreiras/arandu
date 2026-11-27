// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { n0, palavra } from '../../lib/sintese'
import { asnsDoRaio, fmtBR } from './tipos'
import type { Entity } from './tipos'

export const POR_PAGINA_TABELA = 50

/**
 * Tabela do raio (PT-22 / localizador 5.3): as mesmas entidades da lista do painel e do mapa (uma linha por CNPJ, ou por AS sem CNPJ), em texto, com legenda e
 * cabeçalhos de coluna, para quem não usa o mapa. Os ASNs mostrados são os do raio (sede ou prefixo); os do mesmo CNPJ fora do raio só entram na contagem à parte.
 * Paginada de 50 em 50 e recolhida por padrão. IPv6 antes de IPv4. Só o que o mapa já carrega: não traz RPKI nem participação em PTT (o índice de RPKI não vem na camada do mapa).
 */
export function TabelaEntidades({ entities }: { entities: Entity[] }) {
  const [pagina, setPagina] = useState(0)
  const paginas = Math.max(1, Math.ceil(entities.length / POR_PAGINA_TABELA))
  const atual = Math.min(pagina, paginas - 1)
  const linhas = entities.slice(atual * POR_PAGINA_TABELA, (atual + 1) * POR_PAGINA_TABELA)
  return (
    <details className="rounded-lg border border-gray-200 bg-white p-3" data-testid="tabela-localizador">
      <summary className="cursor-pointer select-none text-sm font-medium text-primario-700">Ver as redes e prestadores do raio em tabela ({n0(entities.length)} {palavra(entities.length, 'entidade', 'entidades')})</summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Redes e prestadores no raio, uma linha por CNPJ ou por AS sem CNPJ</caption>
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-600">
              <th scope="col" className="py-1 pr-3 font-medium">Entidade</th>
              <th scope="col" className="py-1 pr-3 font-medium">ASNs no raio</th>
              <th scope="col" className="py-1 pr-3 font-medium">Município e UF</th>
              <th scope="col" className="py-1 pr-3 font-medium">Sede no raio</th>
              <th scope="col" className="py-1 pr-3 font-medium">Prefixos IPv6</th>
              <th scope="col" className="py-1 pr-3 font-medium">Prefixos IPv4</th>
              <th scope="col" className="py-1 pr-3 font-medium">Outorga SCM</th>
              <th scope="col" className="py-1 text-right font-medium">Acessos fixos declarados no raio</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((e) => {
              const doRaio = asnsDoRaio(e)
              const to = e.cnpj ? `/operadora/${e.cnpj}` : `/asn/${e.asns[0]}`
              const fora = e.asnsNoRaio.length ? e.asns.length - e.asnsNoRaio.length : 0
              return (
                <tr key={e.key} className="border-b border-gray-100 text-gray-700 align-top">
                  <th scope="row" className="py-1 pr-3 text-left font-normal">
                    <Link to={to} className="text-primario-700 hover:underline">{e.name || e.cnpj || `AS${e.asns[0]}`}</Link>
                    {e.cnpj && <span className="block font-mono text-xs text-gray-600">{e.cnpj}</span>}
                  </th>
                  <td className="py-1 pr-3 font-mono text-xs">
                    {doRaio.length ? doRaio.map((a) => `AS${a}`).join(', ') : '—'}
                    {fora > 0 && <span className="block font-sans text-gray-600">mais {n0(fora)} {palavra(fora, 'ASN', 'ASNs')} do mesmo CNPJ fora do raio</span>}
                  </td>
                  <td className="py-1 pr-3">{[e.city, e.uf].filter(Boolean).join(', ') || '—'}</td>
                  <td className="py-1 pr-3">{e.asns.length === 0 ? '—' : e.fromHq ? 'sim' : 'não'}</td>
                  <td className="py-1 pr-3">{e.asns.length === 0 ? '—' : e.v6 ? 'sim' : 'não'}</td>
                  <td className="py-1 pr-3">{e.asns.length === 0 ? '—' : e.v4 ? 'sim' : 'não'}</td>
                  <td className="py-1 pr-3">{e.scm ? 'sim' : 'não'}</td>
                  <td className="py-1 text-right tabular-nums">{e.sici ? `${fmtBR(e.sici.acessos)} (${n0(e.sici.municipios)} ${palavra(e.sici.municipios, 'município', 'municípios')})` : '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {paginas > 1 && (
        <div className="mt-2 flex items-center gap-3 text-sm">
          <button type="button" disabled={atual === 0} onClick={() => setPagina(atual - 1)} className="rounded border px-2 py-1 disabled:opacity-40">Anterior</button>
          <span className="text-gray-600">Página {atual + 1} de {paginas}</span>
          <button type="button" disabled={atual + 1 >= paginas} onClick={() => setPagina(atual + 1)} className="rounded border px-2 py-1 disabled:opacity-40">Próxima</button>
        </div>
      )}
      <p className="mt-2 text-xs text-gray-600">Sede no raio e prefixos são do cadastro do Registro.br e da geolocalização dos prefixos; acessos fixos são os declarados ao SICI nos municípios com centro no raio. Estimado e inferido, conforme o selo de cada camada no mapa.</p>
    </details>
  )
}
