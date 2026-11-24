// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { fmt, fmtCnpj } from '../../municipio/ui'

const pct = (v: number) => `${v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`

/**
 * Operadoras na UF, em duas visões: presentes (padrão: quem declara acesso fixo em algum município da UF, com os acessos e a parcela
 * **na UF**) e com sede na UF (acessos declarados no país). Antes só havia a segunda, com acessos nacionais (UF-E2).
 */
export function OperadorasBloco({ dados }: BlocoProps<UfCtx>) {
  const temPresentes = dados.operadorasPresentes.length > 0
  const [visao, setVisao] = useState<'presentes' | 'sede'>(temPresentes ? 'presentes' : 'sede')
  const botao = (v: 'presentes' | 'sede', rotulo: string) => (
    <button type="button" aria-pressed={visao === v} onClick={() => setVisao(v)}
      className={`px-2 py-0.5 rounded border text-xs ${visao === v ? 'border-primario-600 bg-primario-50 text-primario-800' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}>{rotulo}</button>
  )
  return (
    <div>
      {temPresentes && (
        <div className="mb-2 flex flex-wrap items-center gap-2" role="group" aria-label="Quais operadoras">
          {botao('presentes', `Presentes na UF (${fmt(dados.operadorasPresentesTotal)})`)}
          {botao('sede', `Com sede na UF (${fmt(dados.operadorasTotal)})`)}
        </div>
      )}
      {visao === 'presentes' ? (
        <>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                <th scope="col" className="px-2 py-1">Operadora</th><th scope="col" className="px-2 py-1 text-right">Acessos na UF</th>
                <th scope="col" className="px-2 py-1 text-right">Parcela na UF</th><th scope="col" className="px-2 py-1 text-right">Municípios na UF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {dados.operadorasPresentes.map((o) => (
                <tr key={o.cnpj}>
                  <td className="px-2 py-1"><Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">{o.empresa || o.razao_social || fmtCnpj(o.cnpj)}</Link>
                    <div className="text-xs text-gray-500 font-mono">{fmtCnpj(o.cnpj)}{o.uf_sede && <span className="font-sans"> · sede {o.uf_sede}</span>}</div></td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(o.acessos)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{pct(o.share)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(o.municipios)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-gray-500">CNPJs com acesso fixo declarado ao SICI em algum município da UF; acessos e parcela contam só a UF. {dados.operadorasPresentesTotal > dados.operadorasPresentes.length ? `Mostrando as ${dados.operadorasPresentes.length} maiores de ${fmt(dados.operadorasPresentesTotal)}.` : ''}</p>
        </>
      ) : (
        <>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                <th scope="col" className="px-2 py-1">Operadora</th><th scope="col" className="px-2 py-1 text-right">Acessos no país</th><th scope="col" className="px-2 py-1 text-right">Municípios no país</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {dados.operadoras.map((o) => (
                <tr key={o.cnpj}>
                  <td className="px-2 py-1"><Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">{o.empresa || o.razao_social}</Link>
                    <div className="text-xs text-gray-500 font-mono">{fmtCnpj(o.cnpj)}</div></td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(o.acessos)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{fmt(o.municipios)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-gray-500">Operadoras com sede na UF; os acessos são os declarados em todo o país (não só na UF). {dados.operadorasTotal > dados.operadoras.length ? `Mostrando as ${dados.operadoras.length} maiores de ${fmt(dados.operadorasTotal)}.` : ''}</p>
        </>
      )}
    </div>
  )
}
