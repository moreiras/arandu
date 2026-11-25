// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ComoLer } from '../../components/ui/ComoLer'

/** Rótulo de uma S.A. no agrupamento societário (decisão P8): o quadro da Receita traz gestão, não acionistas. Igual ao `grupo_inferivel_rotulo` da API. */
export const ROTULO_SA_NAO_INFERIVEL = 'grupo não inferível pelo quadro societário (S.A.)'

/** O limite em poucas linhas, para o "Como ler" ao lado do rótulo. */
export const COMO_LER_SA = 'O quadro da Receita de uma sociedade anônima traz diretoria e conselho, não acionistas. O agrupamento por quadro societário não alcança esta empresa: ela pode pertencer a um grupo que esta página não mostra. A ligação que vem do quadro de outra empresa em que ela é sócia continua valendo.'

/** Rótulo curto em linha (listas e tabelas). */
export function SeloSA({ className = '' }: { className?: string }) {
  return <span className={`text-xs rounded bg-gray-100 px-1.5 py-0.5 text-gray-600 ${className}`} title={COMO_LER_SA} data-testid="selo-sa">S.A.: quadro societário não informa acionistas</span>
}

/** Rótulo e o "Como ler" com o limite; com `grupoSici` (a string vazia vale "nenhum"), o grupo declarado ao SICI ao lado. */
export function SemInferenciaSA({ grupoSici }: { grupoSici?: string }) {
  const declarado = grupoSici && grupoSici !== 'OUTROS' ? grupoSici : null
  return (
    <div className="space-y-1" data-testid="grupo-nao-inferivel">
      <p className="text-sm text-gray-600">
        <span className="font-medium text-gray-700">{ROTULO_SA_NAO_INFERIVEL}</span>
        {grupoSici !== undefined && <span> · grupo declarado ao SICI: {declarado ? <span className="font-medium text-gray-700">{declarado}</span> : 'nenhum'}</span>}
      </p>
      <ComoLer className="max-w-3xl"><p>{COMO_LER_SA}</p></ComoLer>
    </div>
  )
}
