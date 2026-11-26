// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { limitar, type FraseSintese } from '../../lib/sintese'
import { formatarReferencia } from '../../components/entidade/proveniencia'
import { UNIVERSOS } from '../../lib/universos'
import type { KpiHome } from './kpisBrasilEmNumeros'

export const REGRAS_SINTESE_HOME = 'sintese-home-2'

/**
 * Síntese da Home (PT-22, home 5.1): frases montadas dos mesmos KPIs da faixa "O Brasil em números" (`montarKpis`), sem variação (a variação das
 * faixas segue a regra de comparabilidade da API). Cada frase herda o selo, a fonte e a data do KPI de que sai; KPI sem valor não gera frase.
 */
export function sinteseHome(kpis: { rede: KpiHome[]; mercado: KpiHome[] }): FraseSintese[] {
  const k = (lista: KpiHome[], id: string) => lista.find((x) => x.id === id && x.valor != null)
  const ases = k(kpis.rede, 'ases'), v6 = k(kpis.rede, 'ipv6'), usuarios = k(kpis.rede, 'usuarios')
  const acessos = k(kpis.mercado, 'acessos'), fibra = k(kpis.mercado, 'fibra')
  const de = (x: KpiHome, texto: string): FraseSintese => ({ id: x.id, texto, selo: x.selo, fonte: x.fonte, dataRef: x.dataRef })
  const mes = acessos?.dataRef ? formatarReferencia(acessos.dataRef) : null
  return limitar([
    ases && de(ases, `Este snapshot registra ${ases.valor} ${UNIVERSOS.asnsLacnic.rotulo}.`),
    v6 && de(v6, `Desses ASNs, ${v6.valor} originam ao menos um prefixo IPv6 na tabela global. Ter um bloco IPv6 alocado sem anunciá-lo não entra nessa conta.`),
    acessos && de(acessos, `${mes ? `Em ${mes}, as` : 'No mês de referência, as'} operadoras declararam ao SICI, da Anatel, ${acessos.valor} acessos de banda larga fixa${fibra ? `, dos quais ${fibra.valor} em fibra` : ''}.`),
    usuarios && de(usuarios, `Somando as estimativas do APNIC para cada ASN brasileiro, chega-se a ${usuarios.valor} usuários de Internet. É uma estimativa, não um censo.`),
  ])
}
