// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../../components/entidade/AcoesEntidade'
import { Migalhas } from '../../components/layout/Migalhas'
import { EntityHeader } from '../../components/entidade'

/** Cabeçalho da página de PTT: trilha, nome, UF, data do snapshot e o estado da coleta de cada família de endereços. */
export function CabecalhoPtt({ code, nome, uf, snapshot, temV4, temV6 }: { code: string; nome: string; uf: string; snapshot: string; temV4: boolean; temV6: boolean }) {
  return (
    <EntityHeader
      trilha={<Migalhas grupo="interconexao" itens={[{ rotulo: 'PTTs', to: '/ixps' }, { rotulo: code.toUpperCase(), mono: true }]} />}
      nome={`IX.br ${code.toUpperCase()} — ${nome}`}
      identificadores={[{ rotulo: 'UF', valor: uf }]}
      snapshot={snapshot}
      acoes={<AcoesEntidade tipo="ixp" id={code} />}
    >
      <div className="flex gap-2 mt-2">
        {temV6 ? (
          <span className="text-xs bg-v6-50 text-v6-700 border border-v6-200 rounded px-2 py-0.5">IPv6 ok</span>
        ) : (
          <span className="text-xs bg-gray-100 text-gray-400 border border-gray-200 rounded px-2 py-0.5">IPv6 sem dados</span>
        )}
        {temV4 ? (
          <span className="text-xs bg-primario-50 text-primario-700 border border-primario-200 rounded px-2 py-0.5">IPv4 ok</span>
        ) : (
          <span className="text-xs bg-gray-100 text-gray-400 border border-gray-200 rounded px-2 py-0.5">IPv4 sem dados</span>
        )}
      </div>
    </EntityHeader>
  )
}
