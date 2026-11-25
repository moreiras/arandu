// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import retencao from '../../lib/retencao.gen.json'

type Linha = { id: string; registro: string; contem_ip: boolean; prazo: string; fonte: string }

/**
 * Tabela de retenção gerada das constantes do código (`scripts/gen_retencao.py`, `lib/retencao.gen.json`).
 * Exibida em `/privacidade` (`EXIBIR_TABELA_RETENCAO` em `Privacidade.tsx`), com a redação aprovada pelo mantenedor (PT-13b).
 * `linhas` existe para testes; a página usa o JSON gerado.
 */
export function TabelaRetencao({ linhas = retencao.linhas as Linha[] }: { linhas?: Linha[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left text-gray-600">
        <caption className="text-left text-sm font-semibold text-gray-800 pb-2">Registros e prazos de retenção</caption>
        <thead>
          <tr className="border-b border-gray-200">
            <th scope="col" className="py-2 pr-4 font-semibold">Registro</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Guarda o endereço IP</th>
            <th scope="col" className="py-2 font-semibold">Prazo</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map(l => (
            <tr key={l.id} className="border-b border-gray-100 align-top">
              <th scope="row" className="py-2 pr-4 font-normal">{l.registro}</th>
              <td className="py-2 pr-4">{l.contem_ip ? 'Sim' : 'Não'}</td>
              <td className="py-2">{l.prazo}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
