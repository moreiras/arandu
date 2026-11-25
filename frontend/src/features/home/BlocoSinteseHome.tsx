// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SinteseTopo } from '../../components/ui/SinteseTopo'
import { useKpisHome } from './useKpisHome'
import { REGRAS_SINTESE_HOME, sinteseHome } from './sinteseHome'

/** Síntese no topo da Home: as mesmas consultas da faixa "O Brasil em números" (mesmas chaves, nenhuma chamada a mais). */
export function SinteseHome() {
  const { kpis, data } = useKpisHome()
  return <SinteseTopo frases={sinteseHome(kpis)} snapshot={data} regras={REGRAS_SINTESE_HOME} comoLer="Cada número é uma consulta fixa sobre o snapshot; os mesmos números, com variação, estão em “O Brasil em números”." />
}
