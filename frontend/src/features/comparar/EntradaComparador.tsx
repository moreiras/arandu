// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { lerRecentes, type Recente } from '../../lib/buscaRecentes'
import { urlComparar, type TipoComparacao } from './entidades'

/** Comparações prontas para começar: entidades grandes e conhecidas, para quem chega ao comparador sem uma entidade em mente. */
export const EXEMPLOS: Array<{ tipo: TipoComparacao; rotulo: string; ids: string[]; legenda: string }> = [
  { tipo: 'ixp', rotulo: 'São Paulo × Rio de Janeiro', ids: ['sp', 'rj'], legenda: 'os dois maiores PTTs' },
  { tipo: 'asn', rotulo: 'Google × Cloudflare', ids: ['15169', '13335'], legenda: 'duas CDNs globais (AS15169 e AS13335)' },
  { tipo: 'operadora', rotulo: 'Claro × Vivo', ids: ['66970229000167', '02558157000162'], legenda: 'as duas maiores em acessos fixos declarados' },
  { tipo: 'municipio', rotulo: 'São Paulo × Rio de Janeiro', ids: ['3550308', '3304557'], legenda: 'as duas maiores capitais' },
  { tipo: 'grupo', rotulo: 'Grupo Claro × Vivo', ids: ['grp_66970229', 'ind_02558157'], legenda: 'o grupo da Claro (inferido do quadro societário) e a Vivo' },
]

const NOMES_TIPO: Record<TipoComparacao, string> = { ixp: 'PTTs', asn: 'ASes', operadora: 'Operadoras', municipio: 'Municípios', grupo: 'Grupos' }

/** Tipo e identificador de um caminho de entidade (`/asn/15169`, `/ixp/sp`, `/operadora/…`, `/municipio/…`); `null` para o resto. */
export function entidadeDoCaminho(url: string): { tipo: TipoComparacao; id: string } | null {
  const m = url.split(/[?#]/)[0].match(/^\/(asn|ixp|operadora|municipio|grupo)\/([^/]+)$/)
  if (!m) return null
  return { tipo: m[1] as TipoComparacao, id: decodeURIComponent(m[2]) }
}

/** Painel da página `/comparar` sem nada escolhido: exemplos de um clique e as entidades que a pessoa abriu há pouco (só no navegador, ver `buscaRecentes`). */
export function EntradaComparador({ recentes = lerRecentes() }: { recentes?: Recente[] }) {
  const abertos = recentes.map((r) => ({ r, e: entidadeDoCaminho(r.url) })).filter((x): x is { r: Recente; e: NonNullable<ReturnType<typeof entidadeDoCaminho>> } => !!x.e)
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" aria-label="Como começar" data-testid="entrada-comparador">
      <p className="text-sm text-gray-700">Escolha o que comparar nas abas acima ou comece por um exemplo. A comparação fica no endereço da página, então dá para guardar ou enviar o link.</p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {EXEMPLOS.map((x) => (
          <li key={x.tipo}>
            <Link to={urlComparar(x.tipo, x.ids)} className="block rounded border border-gray-200 px-3 py-2 hover:bg-gray-50">
              <span className="block text-xs text-gray-500">{NOMES_TIPO[x.tipo]}</span>
              <span className="block text-sm font-medium text-primario-700">{x.rotulo}</span>
              <span className="block text-xs text-gray-500">{x.legenda}</span>
            </Link>
          </li>
        ))}
      </ul>
      {abertos.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-600 mb-1">Abertos por você há pouco (comece uma comparação com um deles)</h2>
          <ul className="flex flex-wrap gap-2">
            {abertos.map(({ r, e }) => (
              <li key={r.url}><Link to={urlComparar(e.tipo, [e.id])} className="inline-block rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-700 hover:bg-gray-50" title={r.detalhe}>{NOMES_TIPO[e.tipo].replace(/s$/, '')}: {r.titulo}</Link></li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
