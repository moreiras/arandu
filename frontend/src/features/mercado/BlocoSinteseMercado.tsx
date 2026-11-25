// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { SinteseTopo } from '../../components/ui/SinteseTopo'
import { fetchAcessosMovelStats, fetchAcessosStats } from '../../services/api'
import { useResumo } from '../panorama/useResumo'
import { REGRAS_SINTESE_MERCADO, sinteseMercado } from './sinteseMercado'

/** Síntese no topo do Panorama de mercado. Usa as mesmas consultas e chaves das seções de banda larga fixa e móvel (`/acessos/stats`, rota aberta): nada é buscado duas vezes. */
export function SinteseMercado() {
  const { date } = useResumo()
  const d = date ?? undefined
  const fixo = useQuery({ queryKey: ['acessos-stats', d], queryFn: () => fetchAcessosStats(d, 15), retry: false, staleTime: 10 * 60 * 1000 })
  const movel = useQuery({ queryKey: ['acessos-movel-stats', d], queryFn: () => fetchAcessosMovelStats(d, 15), retry: false, staleTime: 10 * 60 * 1000 })
  return (
    <SinteseTopo frases={sinteseMercado(fixo.data, movel.data)} snapshot={fixo.data?.snapshot_date ?? movel.data?.snapshot_date ?? d} regras={REGRAS_SINTESE_MERCADO}
      comoLer="Acessos declarados pelas empresas à Anatel: não medem receita, qualidade nem pessoas. Fixo e móvel têm meses de referência diferentes e nunca são somados." />
  )
}
