// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { FonteEntrada, ProvenienciaBloco } from './proveniencia'
import { DESCRICAO_SELO, ROTULO_SELO, fonteDe, formatarReferencia, rotuloFrescor } from './proveniencia'

const COR_SELO = { fato: 'bg-fato-50 text-fato-700', inferido: 'bg-inferido-50 text-inferido-700', estimado: 'bg-estimado-50 text-estimado-700' }

/**
 * Rodapé de proveniência de um bloco: selo (fato/inferido/estimado) + fonte, data de referência e coleta, por fonte declarada.
 * `fontes` vem de `sources[]` do manifesto; sem ele, mostra só os ids (nunca inventa data).
 */
export function Provenance({ bloco, fontes, snapshot }: { bloco: ProvenienciaBloco; fontes?: FonteEntrada[] | null; snapshot?: string | null }) {
  const selo = bloco.selo ?? 'fato'
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-400" data-testid="proveniencia">
      <span className={`rounded px-1.5 py-0.5 font-medium ${COR_SELO[selo]}`} title={DESCRICAO_SELO[selo]}>{ROTULO_SELO[selo]}</span>
      {bloco.fontes.map((id) => {
        const f = fonteDe(fontes, id)
        return (
          <span key={id} data-fonte={id}>
            <span className="font-medium text-gray-500">{id}</span>
            {f ? (
              <>
                {' · ref. '}{formatarReferencia(f.as_of)}
                {f.coletado_em ? ` · coletado em ${formatarReferencia(f.coletado_em)}` : ''}
                {f.frescor && f.frescor !== 'ok' ? ` · ${rotuloFrescor(f)}` : ''}
              </>
            ) : fontes ? ' · sem coleta registrada no manifesto (fonte curada pelo projeto)' : ''}
          </span>
        )
      })}
      {bloco.nota && <span>{bloco.nota}</span>}
      {snapshot && <span className="ml-auto">snapshot {formatarReferencia(snapshot)}</span>}
    </div>
  )
}
