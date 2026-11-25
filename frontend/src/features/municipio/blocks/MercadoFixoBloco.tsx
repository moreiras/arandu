// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { TabelaOperadores } from '../TabelaOperadores'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'
import { fmt, hhiLabel } from '../ui'
import { NOTA_FAIXAS_HHI } from '../../../lib/referencias'

export function MercadoFixoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const data = dados.fixo!
  const hhi = hhiLabel(data.hhi)
  return (
    <div className="space-y-5">
      <div className={`text-xs rounded-lg px-3 py-2 border ${hhi.cor}`}>
        HHI {fmt(data.hhi)} sobre acessos declarados: <strong>{hhi.texto}</strong>. {NOTA_FAIXAS_HHI}
        {' '}A contagem de operadoras inclui provedores via satélite, que declaram
        acessos em praticamente todos os municípios do país — por isso o share e o HHI
        descrevem melhor a competição local do que o número bruto de operadoras.
      </div>
      {data.fibra_pct != null && <BarraFibra pct={data.fibra_pct} acessos={data.fibra ?? 0} total={data.acessos} />}
      <TabelaOperadores titulo={`Quem oferece banda larga em ${data.nome}`} operadores={data.operadores} />
    </div>
  )
}

/** Fibra × outros meios (cabo coaxial, rádio, satélite…): uma barra empilhada; o rótulo vem do SICI (meio de acesso "Fibra"). */
function BarraFibra({ pct, acessos, total }: { pct: number; acessos: number; total: number }) {
  const p = Math.max(0, Math.min(100, pct))
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs text-gray-600 mb-1">
        <span>Acessos por fibra óptica</span>
        <span className="tabular-nums"><strong>{pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</strong> · {fmt(acessos)} de {fmt(total)}</span>
      </div>
      <div className="flex h-3 rounded-full overflow-hidden bg-gray-100" role="img" aria-label={`${pct}% dos acessos fixos por fibra`}>
        <div className="bg-mercado-500" style={{ width: `${p}%` }} />
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1"><span>fibra (FTTH/FTTB)</span><span>outros meios</span></div>
    </div>
  )
}
