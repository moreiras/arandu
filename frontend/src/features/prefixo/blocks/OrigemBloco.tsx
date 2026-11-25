// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'
import { FONTE_ORIGEM } from '../sintese'

function LinkAs({ asn, nome }: { asn: number; nome?: string | null }) {
  return <><Link to={`/asn/${asn}`} className="font-mono text-primario-600 hover:underline">AS{asn}</Link>{nome && <span className="ml-2 text-gray-600">{nome}</span>}</>
}

/** Detentor (AS a que o Registro.br associa a alocação) e origem observada (tabela global), cada um com a sua fonte (PFX-E1). */
export function OrigemBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { info } = dados
  const org = info.geo_org
  const det = info.registro_asn ?? null
  const orig = info.observed_origin_asn ?? null
  return (
    <div className="space-y-3 text-sm">
      <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
        <div data-testid="detentor"><dt className="text-xs text-gray-500">Detentor (Registro.br)</dt>
          <dd>{det != null ? <LinkAs asn={det} nome={info.registro_asn_nome} /> : 'não consta das alocações do Registro.br'}
            {det != null && info.escopo === 'rota_dentro_de_alocacao' && info.alocacao_registro_br && (
              <span className="block text-xs text-gray-500">alocação <Link to={`/prefixo/${info.alocacao_registro_br}`} className="font-mono text-primario-600 hover:underline">{info.alocacao_registro_br}</Link>, que contém este prefixo</span>
            )}</dd></div>
        <div data-testid="origem-observada"><dt className="text-xs text-gray-500">Origem observada</dt>
          <dd>{orig != null
            ? <><LinkAs asn={orig} nome={info.observed_origin_nome} /><span className="block text-xs text-gray-500">{FONTE_ORIGEM[info.observed_origin_fonte ?? ''] ?? 'na tabela de roteamento coletada'}{det != null && (orig === det ? '; o mesmo AS do Registro.br' : '; diferente do AS do Registro.br')}</span></>
            : 'sem anúncio deste prefixo, como está, neste snapshot'}</dd></div>
        <div><dt className="text-xs text-gray-500">Organização do detentor</dt>
          <dd>{org?.name ? (org.cnpj ? <Link to={`/operadora/${org.cnpj}`} className="text-primario-600 hover:underline">{org.name}</Link> : org.name) : 'sem dado'}</dd></div>
        <div><dt className="text-xs text-gray-500">Família</dt><dd>IPv{info.ip_version}</dd></div>
      </dl>
      <p className="max-w-3xl text-xs text-gray-500">
        Detentor é o AS que o Registro.br associa ao bloco. Origem observada é o último AS do caminho na tabela global coletada, que guarda
        uma origem por prefixo (fora dela, a vista nos route servers do IX.br). Os dois podem diferir por motivos legítimos, como uma rede
        que anuncia o espaço de uma instituição atendida; a página mostra a diferença sem inferir motivo.
      </p>
    </div>
  )
}
