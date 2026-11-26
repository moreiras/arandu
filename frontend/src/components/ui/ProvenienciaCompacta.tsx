// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Provenance } from '../entidade/Provenance'
import { CitarDado, type PedidoCitacao } from '../entidade/CitarDado'
import type { FonteEntrada, ProvenienciaBloco } from '../entidade/proveniencia'
import { DESCRICAO_SELO, ROTULO_SELO, fonteDe, formatarReferencia } from '../entidade/proveniencia'
import { usaDbIp } from '../../lib/atribuicoes'
import { AtribuicaoDbIp } from './AtribuicaoDbIp'
import { useApresentacaoRecolhida } from './FontesEDatas'
import { SeloMarca } from './SeloMarca'

/**
 * Proveniência em uma linha (selo + primeira fonte e data) com o detalhe completo num popover nativo (`<details>`: abre por clique
 * ou teclado, sem estado do React). O selo continua sempre visível: nada some. Bloco com dado do DB-IP mostra também o link de
 * atribuição, fora do popover, como a licença da base pede.
 *
 * PT-30: dentro de `ApresentacaoRecolhida` o resumo da linha vira só "Fonte e data" (com o selo pequeno); fontes, datas e frescor abrem com
 * um clique, no mesmo `<details>`.
 */
export function ProvenienciaCompacta({ bloco, fontes, snapshot, citacao }: { bloco: ProvenienciaBloco; fontes?: FonteEntrada[] | null; snapshot?: string | null; citacao?: PedidoCitacao }) {
  const selo = bloco.selo ?? 'fato'
  const recolhida = useApresentacaoRecolhida()
  const primeira = bloco.fontes[0]
  const f = primeira ? fonteDe(fontes, primeira) : undefined
  const resumo = [ROTULO_SELO[selo], primeira, f ? `ref. ${formatarReferencia(f.as_of)}` : null].filter(Boolean).join(' · ')
  const detalhe = (
    <details className="relative mt-2 text-xs text-gray-500" data-testid="proveniencia-compacta">
      <summary className={`cursor-pointer select-none list-none ${recolhida ? 'inline-flex min-h-6 items-center gap-1.5 rounded text-primario-700 hover:text-primario-900' : ''}`} title={DESCRICAO_SELO[selo]}>
        {recolhida ? (
          <>
            <SeloMarca selo={selo} />
            Fonte e data
          </>
        ) : (
          <>
            <span className={`mr-1 inline-block h-2 w-2 rounded-full ${selo === 'fato' ? 'bg-fato-600' : selo === 'inferido' ? 'bg-inferido-600' : 'bg-estimado-600'}`} aria-hidden="true" />
            {resumo}{bloco.fontes.length > 1 ? ` +${bloco.fontes.length - 1}` : ''} <span aria-hidden="true">ⓘ</span>
          </>
        )}
      </summary>
      <div className="mt-1 rounded border border-gray-200 bg-white p-2 shadow-sm">
        <Provenance bloco={bloco} fontes={fontes} snapshot={snapshot} />
        {citacao && <CitarDado pedido={citacao} fontes={bloco.fontes} fontesEntradas={fontes} snapshot={snapshot} />}
      </div>
    </details>
  )
  if (!usaDbIp(bloco.fontes)) return detalhe
  return (
    <>
      {detalhe}
      <AtribuicaoDbIp className="mt-1" />
    </>
  )
}
