// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { formatarData } from '../../lib/datas'
import { useDestaquesHome } from './Destaques'

/** "O que mudou" em uma linha: os ASes brasileiros novos confirmados na tabela de roteamento desde o snapshot atual mais antigo (`/brasil/destaques`, aberta) e o caminho para tudo o que mudou. */
export function OQueMudou() {
  const q = useDestaquesHome()
  const m = q.data?.o_que_mudou
  const total = m?.total
  return (
    <p className="text-sm text-gray-700 bg-white border border-gray-200 rounded-lg px-4 py-3" data-testid="o-que-mudou">
      <span className="font-medium text-gray-900">O que mudou: </span>
      {total != null && total > 0
        ? <>{total.toLocaleString('pt-BR')} ASes brasileiros novos confirmados na tabela de roteamento desde {formatarData(m!.de)}{m!.mais_recente ? <>, o mais recente em {formatarData(m!.mais_recente)}</> : null}. </>
        : total === 0 ? `nenhum AS brasileiro novo confirmado desde ${formatarData(m!.de)}. ` : q.isError ? 'não foi possível carregar agora. ' : q.isLoading ? 'carregando… ' : ''}
      <Link to="/mudancas" className="text-primario-700 hover:underline">Ver tudo que mudou →</Link>
    </p>
  )
}
