// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { AccessHistoryChart } from '../../components/acessos/AccessHistoryChart'
import { AccessMunicipioMap } from '../../components/acessos/AccessMunicipioMap'
import type { OperadoraMovelDetalhe } from '../../types/api'
import { Barras, KPI, fmt } from './ui'
import { ehOutorgaSmp } from './servicos'
import { somaValores } from '../../lib/acessos'
import { palavra } from '../../lib/sintese'

/**
 * Seção SMP: outorga móvel + acessos declarados ao SICI móvel. Aparece junto da
 * seção SCM quando o CNPJ tem os dois (as grandes operadoras): a seção "Rede"
 * (ASNs) não se repete aqui porque é a mesma agregação, já mostrada acima.
 */
export function SmpSection({ dataMovel }: { dataMovel: OperadoraMovelDetalhe }) {
  // a outorga própria vem antes do registro sintético de credenciamento (`ehOutorgaSmp`)
  const outorgaSmp = dataMovel.outorgas_smp?.find(ehOutorgaSmp) ?? dataMovel.outorgas_smp?.[0]
  const propria = !!outorgaSmp && ehOutorgaSmp(outorgaSmp)
  const hasSici = dataMovel.acessos != null
  const b2cPct = hasSici && dataMovel.acessos ? (100 * (dataMovel.pf ?? 0)) / dataMovel.acessos : 0

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-1">
          SMP (telefonia móvel){propria && !hasSici && (
            <span className="ml-2 text-xs font-normal text-gray-400">outorgada, sem declaração ao SICI</span>
          )}
        </h2>
        {outorgaSmp && (
          <p className="text-xs text-gray-400">
            {!propria ? 'Sem outorga SMP própria' : outorgaSmp.data_outorga ? <>Outorga SMP desde {outorgaSmp.data_outorga}</> : 'Outorga SMP sem data no cadastro'}
            {outorgaSmp.municipio && <> · sede em {outorgaSmp.municipio}/{outorgaSmp.uf}</>}
          </p>
        )}
        {outorgaSmp?.rede_virtual?.papel === 'credenciada' && (
          <p className="mt-1 text-xs">
            <span className="px-1.5 py-0.5 rounded bg-v6-100 text-v6-800 font-medium">MVNO</span>
            <span className="ml-1.5 text-gray-500">
              credenciada de rede virtual, opera via{' '}
              {outorgaSmp.rede_virtual.prestadora_origem_cnpj ? (
                <Link to={`/operadora/${outorgaSmp.rede_virtual.prestadora_origem_cnpj}`} className="text-primario-600 hover:underline">
                  {outorgaSmp.rede_virtual.prestadora_origem_nome}
                </Link>
              ) : outorgaSmp.rede_virtual.prestadora_origem_nome}
              {!hasSici && '; os acessos de credenciada são declarados pela prestadora de origem (RGST, Resolução Anatel nº 777/2025)'}
            </span>
          </p>
        )}
        {outorgaSmp?.rede_virtual?.papel === 'host' && (
          <p className="mt-1 text-xs">
            <span className="px-1.5 py-0.5 rounded bg-primario-100 text-primario-800 font-medium">Host de rede virtual</span>
            <span className="ml-1.5 text-gray-500">
              credencia {outorgaSmp.rede_virtual.credenciadas_count} {palavra(outorgaSmp.rede_virtual.credenciadas_count, 'operadora MVNO', 'operadoras MVNO')}
            </span>
          </p>
        )}
      </div>

      {hasSici && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          <KPI label="Acessos móveis" value={fmt(dataMovel.acessos)} hint={`mês ${dataMovel.mes_referencia}`} />
          <KPI label="B2C" value={fmt(dataMovel.pf)}
               hint={`${b2cPct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} />
          <KPI label="B2B" value={fmt(dataMovel.pj)}
               hint={`${(100 - b2cPct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} />
          <KPI label="M2M" value={fmt(dataMovel.acessos_m2m)} hint="fora do total ao lado" />
          <KPI label="Municípios" value={fmt(dataMovel.municipios)} />
          <KPI label="Geração predominante" value={dataMovel.geracao_predominante || '—'} />
        </div>
      )}

      {hasSici && dataMovel.acessos_compartilhados && (
        <div className="text-xs text-aviso-800 bg-aviso-50 border border-aviso-100 rounded-lg px-3 py-2">
          Este CNPJ detém {dataMovel.asns.length} ASes. Os acessos móveis são declarados pelo
          CNPJ, não por AS: somar as páginas de cada AS contaria os mesmos assinantes várias vezes.
        </div>
      )}

      {hasSici && (dataMovel.municipios_detalhe?.length ?? 0) > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Onde estão os assinantes móveis</h3>
          <AccessMunicipioMap municipios={dataMovel.municipios_detalhe!} height={360} />
        </div>
      )}

      {hasSici && (dataMovel.serie?.length ?? 0) > 1 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Evolução mensal ({dataMovel.serie!.length} meses)
          </h3>
          <AccessHistoryChart serie={dataMovel.serie!} meses={60} />
        </div>
      )}

      {hasSici && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Geração de rede <span className="font-normal text-gray-500">(todas as linhas, inclusive M2M)</span></h3>
            <Barras dados={dataMovel.por_geracao ?? {}} total={somaValores(dataMovel.por_geracao)} />
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Modalidade de cobrança <span className="font-normal text-gray-500">(todas as linhas, inclusive M2M)</span></h3>
            <Barras dados={dataMovel.por_modalidade ?? {}} total={somaValores(dataMovel.por_modalidade)} />
          </div>
        </div>
      )}
    </div>
  )
}
