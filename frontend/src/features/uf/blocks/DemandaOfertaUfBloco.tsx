// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import type { DemandaOfertaClasse, DemandaOfertaLinha } from '../../../types/api'
import { SITE } from '../../../lib/site'
import { Link } from '../../../components/layout/LinkDatado'
import { ComoLer } from '../../../components/ui/ComoLer'

export const CLASSES: Record<DemandaOfertaClasse, { rotulo: string; cor: string }> = {
  oferta_abaixo_da_demanda: { rotulo: 'oferta abaixo da demanda', cor: 'text-aviso-700' },
  compativel: { rotulo: 'compatível', cor: 'text-gray-700' },
  oferta_acima_da_demanda: { rotulo: 'oferta acima da demanda', cor: 'text-primario-700' },
  indeterminado: { rotulo: 'indeterminado', cor: 'text-gray-400' },
}
export const razao = (v?: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
export const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))

export function intervaloRazao(l: DemandaOfertaLinha) {
  return l.razao_min != null && l.razao_max != null ? `${razao(l.razao_min)} a ${razao(l.razao_max)}` : '—'
}

/**
 * Demanda × oferta de banda larga fixa na UF, ao lado da região e do Brasil. É estimativa do Arandurapé: a demanda vem da proporção de domicílios com banda larga
 * fixa da TIC Domicílios (margem só da amostra); a oferta são os acessos de pessoa física declarados ao SICI. Razão baixa é sinal para investigar, não prova ausência de declaração.
 */
export function DemandaOfertaUfBloco({ dados }: BlocoProps<UfCtx>) {
  const d = dados.demandaOferta
  if (!d) return null
  const linhas = [
    { rotulo: dados.uf, l: d.demanda_oferta },
    ...(d.comparacao.regiao ? [{ rotulo: `Região ${d.regiao}`, l: d.comparacao.regiao }] : []),
    { rotulo: 'Brasil', l: d.comparacao.brasil },
  ]
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
              <th className="px-2 py-1">Recorte</th>
              <th className="px-2 py-1 text-right" title="Domicílios do IBGE projetados × proporção com banda larga fixa (TIC)">Demanda (domicílios)</th>
              <th className="px-2 py-1 text-right" title="Acessos fixos de pessoa física declarados ao SICI">Oferta (acessos PF)</th>
              <th className="px-2 py-1 text-right">Razão (95%)</th>
              <th className="px-2 py-1 text-right" title="max(0, demanda − acessos de pessoa física)">Domicílios sem acesso fixo de PF (estimativa, TIC)</th>
              <th className="px-2 py-1">Leitura</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {linhas.map(({ rotulo, l }) => (
              <tr key={rotulo}>
                <td className="px-2 py-1 font-medium">{rotulo}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(l.demanda_domicilios)}{l.demanda_margem != null && <span className="text-gray-400"> ±{inteiro(l.demanda_margem)}</span>}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(l.oferta_acessos_pf)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{razao(l.razao)}<span className="text-gray-400"> ({intervaloRazao(l)})</span></td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(l.nao_visto)}</td>
                <td className={`px-2 py-1 ${CLASSES[l.classe].cor}`} title={l.motivo}>{CLASSES[l.classe].rotulo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ComoLer>
        <p>Esta aba traz duas estimativas de domicílios sem acesso fixo de pessoa física, com bases diferentes, e elas não coincidem. Na penetração (PNAD), a base é a taxa de domicílios com utilização de Internet, que inclui quem usa só o celular. Aqui, na demanda (TIC Domicílios), a base é a proporção de domicílios com banda larga fixa como principal conexão, com margem de erro da amostra.</p>
      </ComoLer>
      <p className="text-xs text-gray-500">
        Estimativa do {SITE.nome} · TIC Domicílios {d.tic_edicao} (Cetic.br|NIC.br, CC BY 4.0), SICI de {d.mes_referencia_sici ?? 's/d'}, domicílios do IBGE. {d.limites}{' '}
        <Link to="/uso-da-internet" className="text-primario-600 hover:underline">Todas as UFs</Link>.
      </p>
    </div>
  )
}
