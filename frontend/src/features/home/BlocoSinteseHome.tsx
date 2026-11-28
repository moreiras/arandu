// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ResumoEmTexto } from '../../components/ui/ResumoEmTexto'
import { useKpisHome } from './useKpisHome'
import { REGRAS_SINTESE_HOME, sinteseHome } from './sinteseHome'

/** Resumo em texto da Home, depois dos cartões: as mesmas consultas da faixa "O Brasil em números" (mesmas chaves, nenhuma chamada a mais). */
export function SinteseHome() {
  const { kpis, data, dados } = useKpisHome()
  return <ResumoEmTexto frases={sinteseHome(kpis, dados)} snapshot={data} regras={REGRAS_SINTESE_HOME} notaComoLer="Cada número vem de uma consulta fixa ao snapshot. Um bloco IPv6 alocado e não anunciado não entra na contagem de ASNs com IPv6. No IX.br, cada ASN conta uma só vez, e os usuários alcançados somam por ASN, não por PTT. A concentração é o HHI nacional por CNPJ, sem agrupar grupos econômicos." />
}
