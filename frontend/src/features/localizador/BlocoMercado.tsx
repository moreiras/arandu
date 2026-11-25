// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { COLETA_ANATEL, NOTA_COLETA_ANATEL, NOTA_FAIXAS_HHI, rotuloFaixaHhi, faixaHhi } from '../../lib/referencias'
import type { MercadoRaio } from './calculos'

const n = (v: number) => v.toLocaleString('pt-BR')
const MAX_LINHAS = 15

/**
 * Banda larga fixa no raio (PT-26, localizador 5.4): fato declarado, com a regra da participação e o mês à vista. Ordem por acessos, regra escrita.
 * A linha de conformidade declaratória só traz a contagem (nenhum nome): a lista está em "Sem declaração ao SICI".
 */
export function BlocoMercado({ mercado, mesReferencia, snapshot, outorgas }: {
  mercado: MercadoRaio
  mesReferencia: string
  snapshot: string
  outorgas: { total: number; semDeclaracao: number }
}) {
  const linhas = mercado.linhas.slice(0, MAX_LINHAS)
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" aria-labelledby="area-mercado" data-testid="localizador-mercado">
      <h2 id="area-mercado" className="text-titulo-3 text-gray-800">Banda larga fixa no raio <span className="text-xs font-normal text-gray-500">(fato declarado: Anatel, {COLETA_ANATEL}, mês {mesReferencia}; snapshot {snapshot})</span></h2>
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4 text-sm">
        <div><dt className="text-xs text-gray-500">Acessos declarados</dt><dd className="text-lg font-semibold tabular-nums">{n(mercado.acessos)}</dd></div>
        <div><dt className="text-xs text-gray-500">Operadoras (CNPJ)</dt><dd className="text-lg font-semibold tabular-nums">{n(mercado.operadoras)}</dd></div>
        <div><dt className="text-xs text-gray-500">HHI do raio</dt><dd className="text-lg font-semibold tabular-nums">{n(mercado.hhi)} <span className="text-xs font-normal text-gray-500">({rotuloFaixaHhi(faixaHhi(mercado.hhi))})</span></dd></div>
        <div><dt className="text-xs text-gray-500">Maior participação</dt><dd className="text-lg font-semibold tabular-nums">{mercado.maiorParticipacao.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%</dd></div>
      </dl>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <caption className="sr-only">Operadoras de banda larga fixa por acessos declarados nos municípios do raio</caption>
          <thead className="text-xs text-gray-500"><tr><th scope="col" className="px-2 py-1 text-left">CNPJ / empresa</th><th scope="col" className="px-2 py-1 text-right">Acessos no raio</th><th scope="col" className="px-2 py-1 text-right">Participação</th><th scope="col" className="px-2 py-1 text-right">Municípios</th></tr></thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.cnpj} className="border-t border-gray-100">
                <td className="px-2 py-1"><Link to={`/operadora/${l.cnpj}`} className="text-primario-700 hover:underline">{l.empresa || l.cnpj}</Link></td>
                <td className="px-2 py-1 text-right tabular-nums">{n(l.acessos)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{l.participacao.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(l.municipios)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {mercado.linhas.length > MAX_LINHAS && <p className="text-xs text-gray-500">e mais {n(mercado.linhas.length - MAX_LINHAS)} operadoras.</p>}
      <p className="text-xs text-gray-500">
        Regra: participação = acessos declarados pelo CNPJ nos municípios cujo centro está no raio, divididos pelo total desses municípios; o HHI usa a mesma base. Ordem por acessos, do maior para o menor.
        Cada linha é um CNPJ: empresas do mesmo grupo aparecem separadas. {NOTA_FAIXAS_HHI}
      </p>
      {outorgas.total > 0 && (
        <p className="text-xs text-gray-600" data-testid="mercado-sem-declaracao">
          Outorgas SCM com sede no raio: {n(outorgas.total)}; sem acessos declarados em {mesReferencia}: {n(outorgas.semDeclaracao)}. Sem acessos declarados é só um fato sobre a declaração naquele mês; não indica causa.
          {' '}<Link to="/operadoras?visao=sem-declaracao" className="text-primario-700 hover:underline">Ver a lista nacional, com a regra</Link>.
        </p>
      )}
      <p className="text-xs text-gray-500">{NOTA_COLETA_ANATEL}</p>
    </section>
  )
}
