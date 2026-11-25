// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { SCMRecord, SMPRecord, STFCRecord, SEACRecord } from '../../types/api'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../lib/ordenacao'

export function fmtCnpj(c: string): string {
  if (c.length !== 14) return c
  return `${c.slice(0,2)}.${c.slice(2,5)}.${c.slice(5,8)}/${c.slice(8,12)}-${c.slice(12)}`
}

export type OutorgaRecord = SCMRecord | SMPRecord | STFCRecord | SEACRecord

/** "dd/mm/aaaa" → aaaammdd (ordenável); sem data → fim da fila. */
export function dataOutorgaKey(d?: string | null): string {
  const m = d?.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  return m ? `${m[3]}${m[2]}${m[1]}` : d || '99999999'
}

/** Uma linha por CNPJ (dentro do tipo de outorga): a Anatel publica uma linha por
 * registro/endereço, então o mesmo CNPJ aparece várias vezes. Fica o registro mais
 * antigo e a contagem de registros e de municípios distintos (o endereço não é servido). */
export function dedupePorCnpj(outorgas: OutorgaRecord[]) {
  const grupos = new Map<string, OutorgaRecord[]>()
  for (const o of outorgas) {
    const lista = grupos.get(o.cnpj)
    if (lista) lista.push(o)
    else grupos.set(o.cnpj, [o])
  }
  return [...grupos.values()].map((rs) => {
    const ordenados = [...rs].sort((a, b) =>
      dataOutorgaKey(a.data_outorga).localeCompare(dataOutorgaKey(b.data_outorga)),
    )
    const municipios = new Set(rs.map((r) => `${r.municipio ?? ''}/${r.uf ?? ''}`))
    return { rep: ordenados[0], registros: rs.length, municipios: municipios.size }
  })
}

export function OutorgaSection({ outorgas, fonte }: { outorgas: OutorgaRecord[]; fonte: string }) {
  const { ordenados: linhas, props } = useOrdenacao(dedupePorCnpj(outorgas), {
    razao: ({ rep }) => rep.razao_social,
    cnpj: { valor: ({ rep }) => rep.cnpj, primeiro: 'asc' },
    municipio: ({ rep }) => rep.municipio,
    // Sem data vai para o fim (nulo), não para o topo do sentido decrescente.
    data: { valor: ({ rep }) => (rep.data_outorga ? dataOutorgaKey(rep.data_outorga) : null), primeiro: 'asc' },
    situacao: ({ rep }) => rep.situacao,
  })
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 bg-gray-50 border-b border-gray-100">
            <ThOrdenavel {...props('razao')} className="px-4 py-2">Razão Social / Nome Fantasia</ThOrdenavel>
            <ThOrdenavel {...props('cnpj')} className="px-4 py-2 w-36">CNPJ</ThOrdenavel>
            <ThOrdenavel {...props('municipio')} className="px-4 py-2 w-36">Município / UF</ThOrdenavel>
            <ThOrdenavel {...props('data')} className="px-4 py-2 w-28">Data Outorga</ThOrdenavel>
            <ThOrdenavel {...props('situacao')} className="px-4 py-2 w-16">Sit.</ThOrdenavel>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {linhas.map(({ rep: o, registros, municipios }) => (
            <tr key={o.cnpj} className="hover:bg-gray-50">
              <td className="px-4 py-2">
                <div className="font-medium text-gray-900">{o.razao_social}</div>
                {o.nome_fantasia && <div className="text-xs text-gray-400">{o.nome_fantasia}</div>}
                {registros > 1 && (
                  <div className="text-xs text-gray-400 mt-0.5">
                    {registros} registros
                    {municipios > 1 ? ` · ${municipios} municípios` : ''}
                  </div>
                )}
              </td>
              <td className="px-4 py-2 font-mono text-xs text-gray-500">
                <Link to={`/operadora/${o.cnpj}`} className="hover:text-primario-600 hover:underline">
                  {fmtCnpj(o.cnpj)}
                </Link>
              </td>
              <td className="px-4 py-2 text-gray-600 text-sm">
                {municipios > 1 ? `${o.municipio}/${o.uf} e mais ${municipios - 1}` : `${o.municipio}${o.uf ? `/${o.uf}` : ''}`}
              </td>
              <td className="px-4 py-2 text-xs text-gray-500">{o.data_outorga ?? '—'}</td>
              <td className="px-4 py-2">
                {o.situacao && (
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    o.situacao === 'ATI' ? 'bg-ok-100 text-ok-800' :
                    o.situacao === 'EXT' ? 'bg-perigo-100 text-perigo-700' :
                    'bg-aviso-100 text-aviso-800'
                  }`}>{o.situacao}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-4 py-2 border-t border-gray-50 text-xs text-gray-400">
        Fonte: Anatel — dados abertos de outorgas {fonte}
      </div>
    </div>
  )
}

