// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { EventoDeclaracaoMunicipio, IndicadoresMunicipio } from '../../types/api'
import { COLETA_ANATEL, NOTA_COLETA_ANATEL } from '../../lib/referencias'
import { fmtCnpj } from '../operadora/ui'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))

function Linha({ e }: { e: EventoDeclaracaoMunicipio }) {
  const nome = <Link to={`/operadora/${e.cnpj}`} className="text-primario-700 hover:underline">{e.empresa || `CNPJ ${fmtCnpj(e.cnpj)}`}</Link>
  const cnpj = e.empresa ? <span className="text-gray-500"> (CNPJ {fmtCnpj(e.cnpj)})</span> : null
  if (e.tipo === 'sem_declaracao_desde') {
    return (
      <li>{nome}{cnpj}: sem declaração desde {e.mes}; último mês declarado {e.ultimo_mes_declarado ?? '—'}; {n(e.acessos)} acessos neste município em {e.mes_acessos}.</li>
    )
  }
  return <li>{nome}{cnpj}: primeira declaração da série em {e.mes}, com {n(e.acessos)} acessos neste município.</li>
}

/**
 * Faixa de estado do dado do SICI no município (PT-26, MUN 5.1): aparece só quando há evento no mês de referência e diz o fato, sem causa:
 * quem tinha acessos aqui e não declarou nada no mês, e quem declara pela primeira vez na série. Os números de mercado descrevem só o declarado.
 */
export function FaixaDeclaracao({ indicadores }: { indicadores?: IndicadoresMunicipio | null }) {
  const ev = indicadores?.eventos
  if (!ev || ev.length === 0) return null
  return (
    <section aria-label="Declaração de acessos neste município" className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-1.5 text-sm" data-testid="faixa-declaracao">
      <h2 className="text-sm font-semibold text-gray-800">Declaração de acessos neste município <span className="font-normal text-xs text-gray-500">(fato, Anatel; mês de referência {indicadores!.mes_referencia})</span></h2>
      <ul className="list-disc pl-5 text-gray-700">{ev.map((e) => <Linha key={`${e.tipo}-${e.cnpj}`} e={e} />)}</ul>
      <p className="text-xs text-gray-600">Os números de mercado e de penetração descrevem só o que foi declarado. Sem declaração em {indicadores!.mes_referencia} diz só que não há acessos do CNPJ declarados no {COLETA_ANATEL} nesse mês; não indica causa nem intenção.</p>
      <p className="text-xs text-gray-500">{NOTA_COLETA_ANATEL}</p>
    </section>
  )
}
