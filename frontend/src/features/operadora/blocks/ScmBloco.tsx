// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AccessHistoryChart } from '../../../components/acessos/AccessHistoryChart'
import { MapaShareOperadora } from '../MapaShareOperadora'
import { Barras, KPI, fmt, fmtCapacidade } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { OperadoraCtx } from '../contexto'
import { OndeAtua } from '../OndeAtua'

export function ScmBloco({ dados, snapshot }: BlocoProps<OperadoraCtx>) {
  const { data, hasScm, hasSici, b2cPct } = dados
  const municipios = data?.municipios_detalhe ?? []
  return (
    <div className="space-y-5">
          {data && (hasScm || hasSici) && (
            <h2 className="text-base font-semibold text-gray-800 -mb-2">
              SCM (banda larga fixa)
            </h2>
          )}

          {data && hasSici && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
              <KPI label="Acessos" value={fmt(data.acessos)} hint={`mês ${data.mes_referencia}`} />
              <KPI label="B2C" value={fmt(data.pf)}
                   hint={`${b2cPct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} />
              <KPI label="B2B" value={fmt(data.pj)}
                   hint={`${(100 - b2cPct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} />
              <KPI label="Municípios" value={fmt(data.municipios)} />
              <KPI label="Capacidade contratada" value={fmtCapacidade(data.capacidade_mbps)} />
              <KPI label="Velocidade mediana"
                   value={`${fmt(data.velocidade_mediana_mbps != null ? Math.round(data.velocidade_mediana_mbps) : null)} Mbps`}
                   hint={`média ${fmt(data.velocidade_media_mbps != null ? Math.round(data.velocidade_media_mbps) : null)}`} />
            </div>
          )}

          {data && !hasSici && (
            <div className="text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2">
              Outorga SCM sem declaração ao SICI em {dados.indicadores?.mes_referencia ?? data.mes_referencia ?? 'o mês de referência'}.
            </div>
          )}

          {data && hasSici && data.acessos_compartilhados && (
            <div className="text-xs text-aviso-800 bg-aviso-50 border border-aviso-100 rounded-lg px-3 py-2">
              Este CNPJ detém {data.asns.length} ASes. Os acessos são declarados pelo CNPJ,
              não por AS — as páginas de cada um desses ASes mostram este mesmo total, e
              somá-las contaria os mesmos assinantes várias vezes.
            </div>
          )}

          {data && hasSici && (data.municipios_detalhe?.length ?? 0) > 0 && (
            <div>
              <h2 className="text-base font-semibold text-gray-800 mb-2">
                Onde estão os assinantes
              </h2>
              <MapaShareOperadora municipios={data.municipios_detalhe!} />
              <p className="mt-1 text-xs text-gray-600">O mapa tem a alternativa em texto na tabela "Onde atua", abaixo, com os mesmos municípios, a parcela da operadora e o HHI local.</p>
            </div>
          )}

          {data && hasSici && (data.serie?.length ?? 0) > 1 && (
            <div>
              <h2 className="text-base font-semibold text-gray-800 mb-2">
                Evolução mensal ({data.serie!.length} meses)
              </h2>
              <AccessHistoryChart serie={data.serie!} meses={60} />
            </div>
          )}

          {data && hasSici && (
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h2 className="text-sm font-semibold text-gray-700 mb-2">Tecnologia</h2>
                <Barras dados={data.por_tecnologia ?? {}} total={data.acessos ?? 0} />
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h2 className="text-sm font-semibold text-gray-700 mb-2">Faixa de velocidade</h2>
                <Barras dados={data.por_faixa ?? {}} total={data.acessos ?? 0} ordem="faixa" />
              </div>
            </div>
          )}

          {data && hasSici && (data.municipios_detalhe?.length ?? 0) > 0 && (
            <OndeAtua municipios={municipios} mesReferencia={data.mes_referencia ?? dados.indicadores?.mes_referencia} snapshot={snapshot} />
          )}
    </div>
  )
}
