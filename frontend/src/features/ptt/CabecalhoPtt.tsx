// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../../components/entidade/AcoesEntidade'
import { Migalhas } from '../../components/layout/Migalhas'
import { EntityHeader } from '../../components/entidade'
import type { ColetaAfi } from '../../types/api'

/** Rótulo do estado da coleta de uma família; "ok" sozinho não aparece (com a tabela vazia ele escondia zero rotas). */
export function rotuloColeta(familia: 'IPv6' | 'IPv4', coleta: ColetaAfi, rotas: number | null): string {
  if (coleta === 'ok') return `${familia}: ${rotas != null ? rotas.toLocaleString('pt-BR') : '—'} rotas coletadas`
  if (coleta === 'vazia') return `${familia}: coleta feita, zero rotas no looking glass`
  return `${familia}: sem dados neste snapshot`
}

const ESTILO: Record<'IPv6' | 'IPv4', string> = {
  IPv6: 'bg-v6-50 text-v6-700 border-v6-200',
  IPv4: 'bg-primario-50 text-primario-700 border-primario-200',
}

/** Cabeçalho da página de PTT: trilha, nome, UF, data do snapshot e o estado da coleta de cada família de endereços (IPv6 antes). */
export function CabecalhoPtt({ code, nome, uf, snapshot, coletaV4, coletaV6, rotasV4 = null, rotasV6 = null }: {
  code: string; nome: string; uf: string; snapshot: string; coletaV4: ColetaAfi; coletaV6: ColetaAfi; rotasV4?: number | null; rotasV6?: number | null
}) {
  const familias: Array<['IPv6' | 'IPv4', ColetaAfi, number | null]> = [['IPv6', coletaV6, rotasV6], ['IPv4', coletaV4, rotasV4]]
  return (
    <EntityHeader
      trilha={<Migalhas grupo="interconexao" itens={[{ rotulo: 'PTTs', to: '/ixps' }, { rotulo: code.toUpperCase(), mono: true }]} />}
      nome={`IX.br ${code.toUpperCase()} — ${nome}`}
      identificadores={[{ rotulo: 'UF', valor: uf }]}
      snapshot={snapshot}
      acoes={<AcoesEntidade tipo="ixp" id={code} />}
    >
      <div className="flex flex-wrap gap-2 mt-2">
        {familias.map(([f, c, r]) => (
          <span key={f} className={`text-xs border rounded px-2 py-0.5 ${c === 'ok' ? ESTILO[f] : c === 'vazia' ? 'bg-aviso-50 text-aviso-900 border-aviso-200' : 'bg-gray-100 text-gray-600 border-gray-200'}`}>
            {rotuloColeta(f, c, r)}
          </span>
        ))}
      </div>
      {(coletaV6 === 'vazia' || coletaV4 === 'vazia') && (
        <p className="text-xs text-gray-600 mt-1">
          O looking glass do PTT respondeu com a tabela {coletaV6 === 'vazia' && coletaV4 === 'vazia' ? 'vazia nas duas famílias' : `${coletaV6 === 'vazia' ? 'IPv6' : 'IPv4'} vazia`} nesta
          coleta. Zero rotas coletadas não indica que o PTT não tenha rotas nem sessões nessa família; os números que dependem das rotas ficam
          sem valor neste snapshot.
        </p>
      )}
    </EntityHeader>
  )
}
