// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { formatarData } from '../../lib/datas'
import { nomeExibicao } from '../../lib/nomes'

export interface SeloServico { rotulo: string; titulo?: string; tom?: 'neutro' | 'azul' | 'verde' | 'ambar' | 'violeta' | 'laranja' }

const TOM = {
  neutro: 'bg-gray-100 text-gray-700', azul: 'bg-primario-100 text-primario-700', verde: 'bg-ok-100 text-ok-700',
  ambar: 'bg-aviso-100 text-aviso-700', violeta: 'bg-estimado-100 text-estimado-700', laranja: 'bg-alerta-100 text-alerta-700',
}

/**
 * Cabeçalho padrão de entidade: trilha, nome com os selos de serviço/outorga (dentro do h1, como nas páginas de antes),
 * descrição, identificadores/extras e a data do snapshot. `children` recebe o que é próprio da entidade (CNPJ, contatos…).
 */
export function EntityHeader({ tipo, nome, trilha, descricao, identificadores, selos, ladoDoNome, snapshot, acoes, children }: {
  tipo?: string
  nome: string
  trilha?: ReactNode
  descricao?: string
  identificadores?: { rotulo: string; valor: string }[]
  selos?: SeloServico[]
  /** Elementos ao lado do nome, FORA do h1 (selos de outorga, grupo, porte): o nome acessível do título fica só o nome. */
  ladoDoNome?: ReactNode
  snapshot?: string | null
  acoes?: ReactNode
  children?: ReactNode
}) {
  return (
    <header>
      {trilha && <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">{trilha}</div>}
      {tipo && <div className="text-xs uppercase tracking-wide text-gray-400">{tipo}</div>}
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-titulo-1 text-gray-900 flex items-center gap-2">
          {nomeExibicao(nome)}{/\s$/.test(nome) ? ' ' : ''}
          {selos?.map((s) => (
            <span key={s.rotulo} title={s.titulo} className={`text-sm font-normal rounded px-2 py-0.5 ${TOM[s.tom ?? 'neutro']}`}>{s.rotulo}</span>
          ))}
        </h1>
        {ladoDoNome}
        {acoes && <div className="ml-auto">{acoes}</div>}
      </div>
      {descricao && <p className="text-gray-600 text-base mt-1">{descricao}</p>}
      {identificadores && identificadores.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-x-4 text-sm text-gray-500">
          {identificadores.map((i) => <span key={i.rotulo}><span className="text-gray-400">{i.rotulo}</span> {i.valor}</span>)}
        </div>
      )}
      {children}
      {snapshot && (
        <p className="text-gray-400 text-xs mt-1">Snapshot: <span className="font-mono">{formatarData(snapshot)}</span></p>
      )}
    </header>
  )
}
