// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { fmtKm } from '../../../lib/geo'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'
import { KPI, fmt } from '../ui'

/** Indicadores no topo: o que o município tem em acesso (fixo e móvel), mercado (líder e HHI), rede (ASNs próprios) e o PTT mais próximo. */
export function PainelBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const { fixo, movel, proximos, centroide, carregandoPtts } = dados
  const operadores = [...(fixo?.operadores ?? []), ...(movel?.operadores ?? [])]
  const asns = new Set(operadores.flatMap((o) => o.asns))
  const comAsn = (fixo?.operadores ?? []).filter((o) => o.asns.length > 0).length
  const b2cPct = fixo?.acessos ? (100 * fixo.pf) / fixo.acessos : 0
  const ptt = proximos[0]
  return (
    <div className="space-y-2">
      {fixo && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
          <KPI label="Acessos" value={fmt(fixo.acessos)} />
          <KPI label="B2C" value={fmt(fixo.pf)} hint={`${b2cPct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} />
          <KPI label="B2B" value={fmt(fixo.pj)} />
          <KPI label="Operadoras" value={fmt(fixo.operadores_count)} hint={`${comAsn} com ASN próprio`} />
          {fixo.fibra_pct != null && <KPI label="Fibra" value={`${fixo.fibra_pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`} hint="dos acessos fixos (FTTH/FTTB)" />}
          <KPI label="Maior operadora" value={`${fixo.share_maior.toLocaleString('pt-BR')}%`} hint={`HHI ${fmt(fixo.hhi)}`} />
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <KPI label="Acessos móveis" value={movel ? fmt(movel.acessos) : '—'} hint={movel ? `${fmt(movel.operadores_count)} operadoras` : 'sem declaração ao SICI móvel'} />
        <KPI label="Operadoras (fixo + móvel)" value={fmt(new Set(operadores.map((o) => o.cnpj)).size)} />
        <KPI label="ASNs próprios" value={fmt(asns.size)} hint="das operadoras que atendem o município" />
        <KPI label="PTT mais próximo" value={ptt ? ptt.nome : carregandoPtts ? '…' : '—'}
          hint={ptt ? `${fmtKm(ptt.km)} do centróide${dados.conjunto ? ' do município central' : ''}` : centroide ? undefined : 'centróide indisponível'} />
        <KPI label="PTTs a até 100 km" value={centroide ? fmt(proximos.filter((p) => p.km <= 100).length) : '—'} />
      </div>
    </div>
  )
}
