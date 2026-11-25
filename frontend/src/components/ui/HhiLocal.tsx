// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { faixaHhi, rotuloFaixaHhi } from '../../lib/referencias'
import type { FaixaHhi } from '../../types/api'
import { AvisosRecorte } from './AvisoRecorte'

/**
 * HHI local numa célula de tabela: o valor, a faixa do projeto em texto (nunca só cor; a regra e a referência estão em `NOTA_FAIXAS_HHI`) e os avisos de recorte (D6).
 * Sem valor, "—": ausência não é zero. A faixa vem do servidor quando ele a calcula; senão sai da mesma regra (`faixaHhi`).
 */
export function HhiLocal({ valor, faixa, avisos }: { valor: number | null | undefined; faixa?: FaixaHhi | null; avisos?: string[] | null }) {
  if (valor == null) return <span>—</span>
  return (
    <span className="inline-flex flex-col items-end">
      <span className="tabular-nums">{valor.toLocaleString('pt-BR')}</span>
      <span className="text-xs text-gray-600">{rotuloFaixaHhi(faixa ?? faixaHhi(valor))}</span>
      <AvisosRecorte avisos={avisos} />
    </span>
  )
}
