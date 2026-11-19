// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../../components/entidade/AcoesEntidade'
import { Migalhas } from '../../components/layout/Migalhas'
import { EntityHeader } from '../../components/entidade'

/** Cabeçalho do município: trilha com link para a UF, nome e UF (h1 como antes) e a linha de referência do SICI. */
export function CabecalhoMunicipio({ nome, uf, ibge, mesReferencia, snapshot }: { nome: string; uf: string; ibge: string; mesReferencia?: string; snapshot?: string }) {
  return (
    <EntityHeader
      trilha={<Migalhas grupo="territorio" itens={[{ rotulo: uf, to: `/uf/${uf}` }, { rotulo: nome }]} />}
      nome={`${nome} `}
      selos={[{ rotulo: uf }]}
      acoes={<AcoesEntidade tipo="municipio" id={ibge} />}
    >
      <div className="text-sm text-gray-500 mt-0.5">
        Banda larga fixa · IBGE {ibge}{mesReferencia ? ` · mês de referência ${mesReferencia}` : ''}{snapshot ? ` · snapshot ${snapshot}` : ''}
      </div>
    </EntityHeader>
  )
}
