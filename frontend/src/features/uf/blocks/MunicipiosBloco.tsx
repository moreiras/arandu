// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { fmtKm } from '../../../lib/geo'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioUf, UfCtx } from '../contexto'
import { fmt } from '../../municipio/ui'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'

const LIMITE = 15

/**
 * Maiores municípios em acessos (até 15), com o mercado local (operadoras e HHI) e a distância ao PTT. O cabeçalho reordena todos os
 * municípios da UF e só depois corta nos 15 primeiros da coluna escolhida.
 */
export function MunicipiosBloco({ dados }: BlocoProps<UfCtx>) {
  const { ordenados, props } = useOrdenacao<MunicipioUf, 'nome' | 'acessos' | 'operadores' | 'hhi' | 'ptt'>(dados.municipios, {
    nome: (m) => m.nome, acessos: (m) => m.acessos, operadores: (m) => m.operadores, hhi: (m) => m.hhi,
    ptt: { valor: (m) => (m.ptt ? m.kmPtt : null), primeiro: 'asc' },
  }, { campo: 'acessos', dir: 'desc' })
  const lista = ordenados.slice(0, LIMITE)
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
          <ThOrdenavel {...props('nome')} className="px-2 py-1">Município</ThOrdenavel><ThOrdenavel {...props('acessos')} alinhar="right" className="px-2 py-1 text-right">Acessos</ThOrdenavel><ThOrdenavel {...props('operadores')} alinhar="right" className="px-2 py-1 text-right">Operadoras</ThOrdenavel>
          <ThOrdenavel {...props('hhi')} alinhar="right" className="px-2 py-1 text-right">HHI</ThOrdenavel><ThOrdenavel {...props('ptt')} alinhar="right" className="px-2 py-1 text-right">PTT mais próximo</ThOrdenavel>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-50">
        {lista.map((m) => (
          <tr key={m.ibge}>
            <td className="px-2 py-1"><Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">{m.nome}</Link></td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(m.acessos)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(m.operadores)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{fmt(m.hhi)}</td>
            <td className="px-2 py-1 text-right tabular-nums">{m.ptt ? `${m.ptt} · ${fmtKm(m.kmPtt)}` : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
